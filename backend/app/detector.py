"""Detectors return a list of Detection per frame; people carry a track ID.

- YoloDetector: Ultralytics model.track with ByteTrack (the real thing). If our
  weights have no `person` class (our own dataset labels only the items), people
  come from a stock COCO-pretrained model that does the tracking, and our model
  only finds the items. Both lists are merged, so the engine sees the same input.
- FakeDetector: scripted detections so the backend and app can be built and
  demoed before the model exists
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np

from .types import Detection

TRACKER_CFG = Path(__file__).with_name("bytetrack_check.yaml")


def _names(model) -> Dict[int, str]:
    names = model.names
    return names if isinstance(names, dict) else dict(enumerate(names))


def _detections(res, names: Dict[int, str]) -> List[Detection]:
    b = res.boxes
    if b is None or len(b) == 0:
        return []
    ids = b.id.int().tolist() if b.id is not None else [None] * len(b)
    out = []
    for box, conf, cls, tid in zip(b.xyxy.tolist(), b.conf.tolist(), b.cls.int().tolist(), ids):
        label = names[cls]
        out.append(Detection(label, float(conf), tuple(box), tid if label == "person" else None))
    return out


class YoloDetector:
    def __init__(self, weights: str, device: str = "", imgsz: int = 640, low_conf: float = 0.10,
                 person_weights: str = "yolo26n.pt"):
        from ultralytics import YOLO

        self.model = YOLO(weights)
        self.device = device or None
        self.imgsz = imgsz
        self.low_conf = low_conf  # low-score boxes still help ByteTrack keep tracks alive
        self.names = _names(self.model)

        self.person_model = None
        if "person" not in self.names.values():
            self.person_model = YOLO(person_weights)
            self.person_names = _names(self.person_model)
            self.person_cls = next(k for k, v in self.person_names.items() if v == "person")

    @property
    def mode(self) -> str:
        return "two-model" if self.person_model is not None else "single"

    def __call__(self, frame: np.ndarray) -> List[Detection]:
        common = dict(conf=self.low_conf, imgsz=self.imgsz, device=self.device, verbose=False)
        if self.person_model is None:
            res = self.model.track(frame, persist=True, tracker=str(TRACKER_CFG), **common)[0]
            return _detections(res, self.names)
        people = self.person_model.track(frame, persist=True, tracker=str(TRACKER_CFG),
                                         classes=[self.person_cls], **common)[0]
        items = self.model.predict(frame, **common)[0]
        return _detections(people, self.person_names) + _detections(items, self.names)


class FakeDetector:
    """Two people in a 60 s loop: person 2 removes gloves at 20 s and puts them back
    at 35 s; person 1 pulls the mask down at 45 s. Matches the demo script."""

    def __init__(self, period_s: float = 60.0):
        self.period = period_s
        self.t = 0.0

    def __call__(self, frame: np.ndarray, t: float | None = None) -> List[Detection]:
        h, w = frame.shape[:2]
        self.t = (t if t is not None else self.t + 0.1) % self.period
        s = self.t
        out: List[Detection] = []
        for tid, x0 in ((1, 0.15), (2, 0.55)):
            px1, px2 = x0 * w, (x0 + 0.25) * w
            py1, py2 = 0.10 * h, 0.95 * h
            pw = px2 - px1
            out.append(Detection("person", 0.92, (px1, py1, px2, py2), tid))
            face = (px1 + 0.35 * pw, py1 + 0.08 * h, px1 + 0.65 * pw, py1 + 0.15 * h)
            hand_l = (px1, py1 + 0.45 * h, px1 + 0.2 * pw, py1 + 0.53 * h)
            hand_r = (px2 - 0.2 * pw, py1 + 0.45 * h, px2, py1 + 0.53 * h)

            mask_off = tid == 1 and 45 <= s < 55
            gloves_off = tid == 2 and 20 <= s < 35
            out.append(Detection("no_mask" if mask_off else "mask", 0.85, face))
            out.append(Detection("no_gloves" if gloves_off else "gloves", 0.80, hand_l))
            out.append(Detection("gloves", 0.80, hand_r))
        return out


def build_detector(settings):
    if settings.detector == "fake":
        return FakeDetector()
    return YoloDetector(settings.weights, settings.device, settings.imgsz,
                        person_weights=settings.person_weights)
