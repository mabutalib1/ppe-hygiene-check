import io
import json
import time
import urllib.error

import numpy as np
import pytest

from app import camera as camera_mod
from app import nebras
from app.camera import LatestFrameReader
from app.nebras import NebrasClient, NebrasError, NebrasLiveSource

CH = "11111111-1111-1111-1111-111111111111"
SECRET_URL = "https://vendor.example/live.m3u8?token=SECRET"


class FakeNebras:
    """Stands in for urllib.request.urlopen and records every call."""

    def __init__(self, cameras=None, live=None):
        self.calls = []
        self.cameras = cameras if cameras is not None else [
            {"id": CH, "provider": "dahua", "name": "منطقة الكاشير", "nameEn": "Cashier",
             "branchName": "Nahdah", "online": True, "canPlay": True}]
        self.live = live or {"protocol": "hls", "url": SECRET_URL, "leaseId": "lease-1"}
        self.expire_token_once = False
        self.leases = 0

    def __call__(self, req, timeout=None):
        method, url = req.get_method(), req.full_url
        auth = req.headers.get("Authorization")
        self.calls.append((method, url.split("nebras.test", 1)[1], auth))
        path = url.split("nebras.test", 1)[1]
        if path == "/auth/login":
            body = json.loads(req.data)
            if body != {"email": "a@b.c", "password": "pw"}:
                return self._error(req, 401)
            return self._ok({"access_token": f"jwt{len(self.calls)}"})
        if self.expire_token_once:
            self.expire_token_once = False
            return self._error(req, 401)
        if path.startswith("/camera-cloud/viewer"):
            return self._ok({"brandId": "b1", "cameras": self.cameras, "views": []})
        if path.endswith("/live") and method == "POST":
            self.leases += 1
            return self._ok(dict(self.live, leaseId=f"lease-{self.leases}") if "leaseId" in self.live
                            else self.live)
        if path.startswith("/camera-cloud/live/"):
            return self._ok(None)
        return self._error(req, 404)

    @staticmethod
    def _ok(data):
        return io.BytesIO(b"" if data is None else json.dumps(data).encode())

    @staticmethod
    def _error(req, code):
        raise urllib.error.HTTPError(req.full_url, code, "err", {}, io.BytesIO(b'{"message":"x"}'))

    def paths(self, method=None):
        return [p for m, p, _ in self.calls if method is None or m == method]


@pytest.fixture
def api(monkeypatch):
    fake = FakeNebras()
    monkeypatch.setattr(nebras.urllib.request, "urlopen", fake)
    return fake


def client():
    return NebrasClient("https://nebras.test", brand_id="b1", email="a@b.c", password="pw")


def test_login_inventory_and_live(api):
    c = client()
    assert c.cameras()[0]["id"] == CH
    live = c.start_live(CH, "hd")
    assert live["protocol"] == "hls"
    assert api.paths()[0] == "/auth/login"
    assert api.paths()[1] == "/camera-cloud/viewer?brandId=b1"
    assert ("POST", f"/camera-cloud/channels/{CH}/live") in [(m, p) for m, p, _ in api.calls]
    assert all(a == "Bearer jwt1" for m, p, a in api.calls[1:])


def test_relogin_once_when_token_expires(api):
    c = client()
    c.cameras()
    api.expire_token_once = True
    c.cameras()
    assert api.paths().count("/auth/login") == 2


def test_bad_password_is_a_clear_error(api):
    c = NebrasClient("https://nebras.test", brand_id="b1", email="a@b.c", password="wrong")
    with pytest.raises(NebrasError, match="sign-in failed"):
        c.cameras()


def test_live_source_lifecycle(api):
    src = NebrasLiveSource(client(), CH, renew_every_s=0)
    url = src.open()
    assert url == SECRET_URL and src.lease_id == "lease-1" and src.label == "Cashier (Nahdah)"
    assert src.keepalive()
    assert ("PATCH", "/camera-cloud/live/lease-1") in [(m, p) for m, p, _ in api.calls]
    src.open()  # reconnect: old lease released, never reused
    assert ("DELETE", "/camera-cloud/live/lease-1") in [(m, p) for m, p, _ in api.calls]
    assert src.lease_id == "lease-2"
    src.close()
    src.close()  # idempotent
    assert api.paths("DELETE") == ["/camera-cloud/live/lease-1", "/camera-cloud/live/lease-2"]


@pytest.mark.parametrize("cam,msg", [
    ({"id": CH, "online": False, "canPlay": False}, "offline"),
    ({"id": CH, "online": None, "canPlay": False}, "not playable"),
    ({"id": "other", "canPlay": True}, "not found"),
])
def test_unplayable_cameras_fail_closed(monkeypatch, cam, msg):
    fake = FakeNebras(cameras=[cam])
    monkeypatch.setattr(nebras.urllib.request, "urlopen", fake)
    with pytest.raises(NebrasError, match=msg):
        NebrasLiveSource(client(), CH).open()
    assert fake.paths("POST")[1:] == []  # no live session was requested


def test_hikvision_is_refused(monkeypatch):
    fake = FakeNebras(live={"protocol": "hikvision-sdk", "url": "ezopen://x",
                            "sdk": {"accessToken": "t"}})
    monkeypatch.setattr(nebras.urllib.request, "urlopen", fake)
    with pytest.raises(NebrasError, match="only HLS") as e:
        NebrasLiveSource(client(), CH).open()
    assert "ezopen" not in str(e.value) and "accessToken" not in str(e.value)


class FakeCapture:
    opened = []

    def __init__(self, url, *args):
        FakeCapture.opened.append(url)
        self.left = 3

    def isOpened(self):
        return True

    def read(self):
        self.left -= 1
        return (self.left >= 0), np.zeros((4, 4, 3), np.uint8)

    def release(self):
        pass


def test_reader_reconnects_with_a_fresh_session(api, monkeypatch, caplog):
    FakeCapture.opened = []
    monkeypatch.setattr(camera_mod.cv2, "VideoCapture", FakeCapture)
    src = NebrasLiveSource(client(), CH)
    reader = LatestFrameReader("nebras", live=src).start()
    deadline = time.time() + 5
    while len(FakeCapture.opened) < 2 and time.time() < deadline:
        time.sleep(0.05)
    reader.stop()
    time.sleep(0.1)
    assert len(FakeCapture.opened) >= 2           # stream ended → reconnected
    assert reader.read()[0] is not None
    assert "/camera-cloud/live/lease-1" in api.paths("DELETE")  # first lease released
    assert src.lease_id is None                    # stop released the current one
    assert "SECRET" not in caplog.text             # the stream URL never reaches the logs


def test_server_reports_missing_config(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("DETECTOR", "fake")
    monkeypatch.setenv("CAMERA_SOURCE", "nebras")
    monkeypatch.setenv("NEBRAS_CHANNEL_ID", "")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import app
    with TestClient(app) as c:
        deadline = time.time() + 3
        while time.time() < deadline:
            h = c.get("/health").json()
            if h["camera"]["error"]:
                break
            time.sleep(0.05)
    assert h["ok"] is False and h["camera"]["connected"] is False
    assert "NEBRAS_CHANNEL_ID" in h["camera"]["error"]
