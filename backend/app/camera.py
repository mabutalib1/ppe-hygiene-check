"""Camera reader that always hands out the newest frame (never builds a delay)."""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger("check.camera")
# OpenCV/FFmpeg timeouts for network streams, so a dead stream reconnects instead of hanging
NET_TIMEOUTS = [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 15000]


def _parse_source(src: str):
    return int(src) if src.isdigit() else src


def _is_file(src) -> bool:
    return isinstance(src, str) and not src.startswith(("rtsp://", "http://", "https://"))


class LatestFrameReader:
    """Background thread reading frames; `read()` returns the most recent one.

    Sources: RTSP/HTTP URL (CCTV or phone IP-camera app), webcam index ("0"),
    a video file (demo backup, paced at its own fps and looped), "synthetic", or a
    live session source (`live`, e.g. the shop camera through Nebras) that hands
    out a fresh stream URL on every connect.
    """

    def __init__(self, source: str, loop_video: bool = True, live=None):
        self.source = source
        self.loop_video = loop_video
        self.live = live
        self._frame: Optional[np.ndarray] = None
        self._frame_t = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.connected = False
        self.last_error: Optional[str] = None   # safe to show (never contains stream URLs)
        self._thread = threading.Thread(target=self._run, daemon=True, name="camera")

    def start(self) -> "LatestFrameReader":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self.live is not None:
            self.live.close()  # release the live lease now; the thread may be mid-read

    def read(self) -> Tuple[Optional[np.ndarray], float]:
        with self._lock:
            return self._frame, self._frame_t

    def _publish(self, frame: np.ndarray) -> None:
        with self._lock:
            self._frame, self._frame_t = frame, time.time()

    def _run(self) -> None:
        if self.live is not None:
            self._run_live()
            return
        if self.source == "synthetic":
            self._run_synthetic()
            return
        src = _parse_source(self.source)
        is_file = _is_file(src) and not isinstance(src, int)
        while not self._stop.is_set():
            cap = cv2.VideoCapture(src)
            if not cap.isOpened():
                self.connected = False
                time.sleep(2.0)  # camera not reachable yet: retry
                continue
            self.connected = True
            delay = 1.0 / (cap.get(cv2.CAP_PROP_FPS) or 30.0) if is_file else 0.0
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    break
                self._publish(frame)
                if delay:
                    time.sleep(delay)
            cap.release()
            self.connected = False
            if is_file and not self.loop_video:
                return
            if not is_file:
                time.sleep(1.0)

    def _run_live(self) -> None:
        backoff = 5.0
        while not self._stop.is_set():
            try:
                url = self.live.open()
            except Exception as e:  # NebrasError messages are safe; others: type only
                self.last_error = str(e) if hasattr(e, "status") else f"live source error ({type(e).__name__})"
                log.warning("live camera unavailable: %s (retry in %ds)", self.last_error, backoff)
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 120.0)
                continue
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG, NET_TIMEOUTS)
            del url  # the stream URL is a credential: don't keep or log it
            if not cap.isOpened():
                cap.release()
                self.live.close()
                self.last_error = "could not open the live stream"
                log.warning("%s (retry in %ds)", self.last_error, backoff)
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 120.0)
                continue
            self.connected, self.last_error, backoff = True, None, 5.0
            log.info("live camera connected: %s", self.live.label)
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    self.last_error = "live stream stopped"
                    break
                self._publish(frame)
                if not self.live.keepalive():
                    self.last_error = "live session ended"
                    break
            cap.release()
            self.connected = False
            self.live.close()
            if not self._stop.is_set():
                log.info("%s, reconnecting", self.last_error)
                self._stop.wait(2.0)
        self.live.close()

    def _run_synthetic(self) -> None:
        self.connected = True
        while not self._stop.is_set():
            frame = np.full((720, 1280, 3), 40, np.uint8)
            cv2.putText(frame, "SYNTHETIC CAMERA", (40, 690), cv2.FONT_HERSHEY_SIMPLEX,
                        1.2, (200, 200, 200), 2)
            self._publish(frame)
            time.sleep(1 / 30)
