"""The processing loop: camera → detector/tracker → violation logic → outputs."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Callable, List, Optional

import cv2

from .camera import LatestFrameReader
from .detector import FakeDetector
from .draw import annotate
from .engine import ViolationEngine
from .store import EventStore

log = logging.getLogger("check.processor")


def iso(t: float) -> str:
    return datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")


class Processor:
    def __init__(self, camera: LatestFrameReader, detector, engine: ViolationEngine,
                 store: EventStore, target_fps: float = 10.0, status_hz: float = 2.0):
        self.camera = camera
        self.detector = detector
        self.engine = engine
        self.store = store
        self.min_dt = 1.0 / target_fps if target_fps > 0 else 0.0
        self.status_dt = 1.0 / status_hz if status_hz > 0 else 0.5
        self.on_message: Callable[[dict], None] = lambda m: None

        self.latest_jpeg: Optional[bytes] = None
        self.latest_status: List[dict] = []
        self.fps = 0.0
        self.last_error: Optional[str] = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="processor")
        self._start = time.time()

    def start(self) -> "Processor":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def _detect(self, frame, t):
        if isinstance(self.detector, FakeDetector):
            return self.detector(frame, t - self._start)
        return self.detector(frame)

    def _run(self) -> None:
        last_frame_t, last_status, last_tick = 0.0, 0.0, time.time()
        while not self._stop.is_set():
            frame, frame_t = self.camera.read()
            now = time.time()
            if frame is None or frame_t == last_frame_t or now - last_tick < self.min_dt:
                time.sleep(0.005)
                continue
            last_frame_t = frame_t
            dt, last_tick = now - last_tick, now
            self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt) if self.fps else 1.0 / dt
            try:
                self._step(frame, now)
                self.last_error = None
            except Exception as e:  # keep the loop alive during a demo
                self.last_error = repr(e)
                log.exception("processing step failed")
                time.sleep(0.2)
                continue
            if now - last_status >= self.status_dt:
                last_status = now
                self.on_message({"type": "status", "people": self.latest_status,
                                 "fps": round(self.fps, 1)})

    def _step(self, frame, t: float) -> None:
        h, w = frame.shape[:2]
        dets = self._detect(frame, t)
        status, events = self.engine.update(t, dets, (w, h))
        img = annotate(frame, dets, status, self.engine.track_to_pid())
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            self.latest_jpeg = buf.tobytes()
        self.latest_status = status

        for ev in events:
            ev = {**ev, "time": iso(ev.pop("t"))}
            if ev["type"] == "violation":
                snap = self.store.snapshot_path(ev["event_id"])
                if ok:
                    snap.write_bytes(buf.tobytes())
                self.store.add(ev, snap.name if ok else None)
                ev["snapshot_url"] = f"/snapshots/{ev['event_id']}.jpg" if ok else None
            else:
                self.store.resolve(ev["event_id"], ev["time"], ev["duration_s"])
            log.info("event %s", ev)
            self.on_message(ev)
