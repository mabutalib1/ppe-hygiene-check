"""Camera reader that always hands out the newest frame (never builds a delay)."""
from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np


def _parse_source(src: str):
    return int(src) if src.isdigit() else src


def _is_file(src) -> bool:
    return isinstance(src, str) and not src.startswith(("rtsp://", "http://", "https://"))


class LatestFrameReader:
    """Background thread reading frames; `read()` returns the most recent one.

    Sources: RTSP/HTTP URL (CCTV or phone IP-camera app), webcam index ("0"),
    a video file (demo backup, paced at its own fps and looped), or "synthetic".
    """

    def __init__(self, source: str, loop_video: bool = True):
        self.source = source
        self.loop_video = loop_video
        self._frame: Optional[np.ndarray] = None
        self._frame_t = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.connected = False
        self._thread = threading.Thread(target=self._run, daemon=True, name="camera")

    def start(self) -> "LatestFrameReader":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def read(self) -> Tuple[Optional[np.ndarray], float]:
        with self._lock:
            return self._frame, self._frame_t

    def _publish(self, frame: np.ndarray) -> None:
        with self._lock:
            self._frame, self._frame_t = frame, time.time()

    def _run(self) -> None:
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

    def _run_synthetic(self) -> None:
        self.connected = True
        while not self._stop.is_set():
            frame = np.full((720, 1280, 3), 40, np.uint8)
            cv2.putText(frame, "SYNTHETIC CAMERA", (40, 690), cv2.FONT_HERSHEY_SIMPLEX,
                        1.2, (200, 200, 200), 2)
            self._publish(frame)
            time.sleep(1 / 30)
