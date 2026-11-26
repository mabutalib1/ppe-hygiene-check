"""Live camera feed from the shop, through the Nebras camera API.

The backend signs in to Nebras with an admin account, starts a live session for
one camera channel, and reads the vendor's HLS stream with OpenCV, so the model
runs on the real shop camera instead of a recorded clip.

Flow (see the Nebras camera viewer handoff):
    POST /auth/login                          -> access_token (admin JWT)
    GET  /camera-cloud/viewer?brandId=...     -> cameras (online, canPlay, provider)
    POST /camera-cloud/channels/:id/live      -> {"protocol": "hls", "url", "leaseId"}
    PATCH  /camera-cloud/live/:leaseId        every ~10 min while open
    DELETE /camera-cloud/live/:leaseId        on close / before reconnecting

Only providers that return plain HLS (Dahua) can be read on a server. Hikvision
returns "hikvision-sdk", which needs the vendor's browser decoder, so it is refused
with a clear error.

Secrets: the JWT, password and the live URL are never logged, put in errors, or
returned by the API. Set them as environment variables, never in git.

List the cameras of the brand (to pick NEBRAS_CHANNEL_ID):
    python -m app.nebras cameras
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

log = logging.getLogger("check.nebras")

DEFAULT_API_URL = "https://api.nebrasinsights.com"
RENEW_EVERY_S = 600.0        # handoff: renew the lease about every 10 minutes
RENEW_RETRY_S = 60.0         # a failed renew is retried; the server keeps a lease 30 min


class NebrasError(Exception):
    """Failure talking to Nebras. The message is safe to show (no tokens or URLs)."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


def _server_message(body: bytes) -> str:
    """The short reason a 400 carries (NestJS style {"message": ...}), if any."""
    try:
        data = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return ""
    msg = data.get("message") if isinstance(data, dict) else None
    if isinstance(msg, list):
        msg = "; ".join(str(m) for m in msg)
    return str(msg)[:200] if msg else ""


class NebrasClient:
    """Small Nebras camera API client (standard library only)."""

    def __init__(self, api_url: str = DEFAULT_API_URL, brand_id: str = "", email: str = "",
                 password: str = "", token: str = "", company_slug: str = "",
                 timeout: float = 15.0):
        self.api_url = (api_url or DEFAULT_API_URL).rstrip("/")
        self.brand_id = brand_id
        self.email = email
        self._password = password
        self._token = token
        self.company_slug = company_slug
        self.timeout = timeout

    def __repr__(self) -> str:  # never show the token or password
        return f"NebrasClient(api_url={self.api_url!r}, brand_id={self.brand_id!r})"

    # ---- auth ----
    @property
    def can_login(self) -> bool:
        return bool(self.email and self._password)

    def login(self) -> None:
        if not self.can_login:
            raise NebrasError("set NEBRAS_EMAIL and NEBRAS_PASSWORD (or NEBRAS_TOKEN)")
        data = self._send("POST", "/auth/login",
                          {"email": self.email, "password": self._password}, auth=False)
        token = data.get("access_token") if isinstance(data, dict) else None
        if not token:
            raise NebrasError("Nebras sign-in returned no access_token")
        self._token = token
        log.info("signed in to Nebras as %s", self.email)

    # ---- HTTP ----
    def _send(self, method: str, path: str, body: Optional[dict] = None,
              auth: bool = True) -> Any:
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if auth:
            headers["Authorization"] = f"Bearer {self._token}"
            if self.company_slug:
                headers["X-Company-Slug"] = self.company_slug
        req = urllib.request.Request(self.api_url + path, data=data, method=method,
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raise self._http_error(e.code, e.read() if e.fp else b"", auth) from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            reason = getattr(e, "reason", e)
            raise NebrasError(f"Nebras API not reachable ({type(reason).__name__})") from None
        return json.loads(raw) if raw.strip() else None

    @staticmethod
    def _http_error(code: int, body: bytes, auth: bool) -> NebrasError:
        if code == 401:
            msg = ("Nebras sign-in failed: check NEBRAS_EMAIL / NEBRAS_PASSWORD" if not auth
                   else "Nebras session expired or invalid")
        elif code == 403:
            msg = "this Nebras account has no camera access for the brand (needs an admin grant)"
        elif code == 400:
            msg = _server_message(body) or "Nebras refused the request (camera or branch unavailable)"
        elif code == 404:
            msg = "Nebras: not found, check NEBRAS_BRAND_ID / NEBRAS_CHANNEL_ID and that the camera service is on"
        else:
            msg = f"Nebras API error {code}"
        return NebrasError(msg, code)

    def request(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        """Authenticated request; signs in first, and once more when the JWT expires."""
        if not self._token:
            self.login()
        try:
            return self._send(method, path, body)
        except NebrasError as e:
            if e.status != 401 or not self.can_login:
                raise
        self.login()
        return self._send(method, path, body)

    # ---- camera API ----
    def inventory(self) -> Dict[str, Any]:
        if not self.brand_id:
            raise NebrasError("NEBRAS_BRAND_ID is not set")
        q = urllib.parse.urlencode({"brandId": self.brand_id})
        return self.request("GET", f"/camera-cloud/viewer?{q}") or {}

    def cameras(self) -> List[Dict[str, Any]]:
        return list(self.inventory().get("cameras") or [])

    def start_live(self, channel_id: str, quality: str = "hd") -> Dict[str, Any]:
        cid = urllib.parse.quote(channel_id, safe="")
        return self.request("POST", f"/camera-cloud/channels/{cid}/live", {"quality": quality}) or {}

    def renew(self, lease_id: str) -> None:
        self.request("PATCH", f"/camera-cloud/live/{urllib.parse.quote(lease_id, safe='')}")

    def release(self, lease_id: str) -> None:
        """Best effort: the server also expires abandoned leases after 30 minutes."""
        try:
            self.request("DELETE", f"/camera-cloud/live/{urllib.parse.quote(lease_id, safe='')}")
        except NebrasError as e:
            log.warning("could not release the live lease: %s", e)


def camera_label(cam: Dict[str, Any]) -> str:
    name = cam.get("nameEn") or cam.get("name") or cam.get("id", "?")
    branch = cam.get("branchName")
    return f"{name} ({branch})" if branch else str(name)


class NebrasLiveSource:
    """One live session for one channel, opened fresh on every (re)connect.

    The camera reader calls open() to get a stream URL, keepalive() between frames,
    and close() when the stream ends or the server stops. A lease or URL is never
    reused after a reconnect.
    """

    def __init__(self, client: NebrasClient, channel_id: str, quality: str = "hd",
                 renew_every_s: float = RENEW_EVERY_S):
        if quality not in ("hd", "fluent"):
            raise ValueError("NEBRAS_QUALITY must be 'hd' or 'fluent'")
        self.client = client
        self.channel_id = channel_id
        self.quality = quality
        self.renew_every_s = renew_every_s
        self.label = "nebras"
        self.lease_id: Optional[str] = None
        self._next_renew = 0.0
        self._lock = threading.Lock()

    def open(self) -> str:
        """Start a new live session and return its stream URL (keep it out of logs)."""
        self.close()
        if not self.channel_id:
            raise NebrasError("NEBRAS_CHANNEL_ID is not set (run: python -m app.nebras cameras)")
        cam = next((c for c in self.client.cameras() if c.get("id") == self.channel_id), None)
        if cam is None:
            raise NebrasError("camera channel not found in this brand (check NEBRAS_CHANNEL_ID)")
        self.label = camera_label(cam)
        if not cam.get("canPlay"):
            state = "offline" if cam.get("online") is False else "not playable (no branch or unknown state)"
            raise NebrasError(f"camera {self.label} is {state}")

        live = self.client.start_live(self.channel_id, self.quality)
        lease = live.get("leaseId")
        if live.get("protocol") != "hls" or not live.get("url"):
            if lease:
                self.client.release(lease)
            raise NebrasError(
                f"camera {self.label} streams as '{live.get('protocol')}', only HLS (Dahua) "
                "cameras can be read by the server; pick a Dahua channel")
        with self._lock:
            self.lease_id = lease
            self._next_renew = time.monotonic() + self.renew_every_s
        log.info("live session started for %s (%s)", self.label, self.quality)
        return live["url"]

    def keepalive(self) -> bool:
        """Renew the lease when due. False means the lease is gone: reconnect."""
        with self._lock:
            lease = self.lease_id
            due = lease is not None and time.monotonic() >= self._next_renew
        if not due:
            return True
        try:
            self.client.renew(lease)
        except NebrasError as e:
            if e.status in (400, 404):
                log.warning("live lease ended (%s), reconnecting", e)
                return False
            log.warning("lease renew failed (%s), retrying in %ds", e, RENEW_RETRY_S)
            with self._lock:
                self._next_renew = time.monotonic() + RENEW_RETRY_S
            return True
        with self._lock:
            self._next_renew = time.monotonic() + self.renew_every_s
        return True

    def close(self) -> None:
        with self._lock:
            lease, self.lease_id = self.lease_id, None
        if lease:
            self.client.release(lease)


def from_settings(s) -> NebrasLiveSource:
    client = NebrasClient(api_url=s.nebras_api_url, brand_id=s.nebras_brand_id,
                          email=s.nebras_email, password=s.nebras_password,
                          token=s.nebras_token, company_slug=s.nebras_company_slug)
    return NebrasLiveSource(client, s.nebras_channel_id, s.nebras_quality)


def _print_cameras() -> int:
    from .config import Settings
    s = Settings.from_env()
    try:
        cams = from_settings(s).client.cameras()
    except NebrasError as e:
        print(f"error: {e}")
        return 1
    if not cams:
        print("no cameras for this brand")
        return 0
    print(f"{'channel id':38} {'provider':9} {'online':7} {'play':5} camera")
    for c in sorted(cams, key=lambda c: (str(c.get("branchName")), str(c.get("nameEn") or c.get("name")))):
        online = {True: "yes", False: "no"}.get(c.get("online"), "?")
        play = "yes" if c.get("canPlay") else "no"
        print(f"{c.get('id', ''):38} {str(c.get('provider', '')):9} {online:7} {play:5} {camera_label(c)}")
    print("\nOnly 'dahua' (HLS) cameras with play=yes work in the backend.")
    return 0


if __name__ == "__main__":
    import sys
    if sys.argv[1:] != ["cameras"]:
        print("usage: python -m app.nebras cameras")
        sys.exit(2)
    sys.exit(_print_cameras())
