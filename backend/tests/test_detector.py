"""YoloDetector with a fake `ultralytics` module (no weights, no GPU)."""
import sys
import types

import numpy as np
import pytest


class T(list):
    """Just enough of a tensor: .tolist() and .int()."""

    def tolist(self):
        return list(self)

    def int(self):
        return T(int(v) for v in self)


class Boxes:
    def __init__(self, rows, ids=None):
        self.xyxy = T([r[:4] for r in rows])
        self.conf = T([r[4] for r in rows])
        self.cls = T([r[5] for r in rows])
        self.id = T(ids) if ids is not None else None

    def __len__(self):
        return len(self.conf)


class FakeYOLO:
    """COCO-like stock model when the file name starts with 'yolo', else our model."""
    calls = []

    def __init__(self, weights):
        self.weights = weights
        if weights.startswith("yolo"):
            self.names = {0: "person", 1: "bicycle"}
        else:
            self.names = FakeYOLO.our_names

    def track(self, frame, **kw):
        FakeYOLO.calls.append((self.weights, "track", kw.get("classes")))
        if self.weights.startswith("yolo"):
            return [types.SimpleNamespace(boxes=Boxes([(0, 0, 100, 300, 0.9, 0)], ids=[7]))]
        return [types.SimpleNamespace(boxes=Boxes([(0, 0, 100, 300, 0.9, 0), (10, 10, 30, 30, 0.8, 1)],
                                                  ids=[3, 4]))]

    def predict(self, frame, **kw):
        FakeYOLO.calls.append((self.weights, "predict", None))
        return [types.SimpleNamespace(boxes=Boxes([(10, 150, 30, 170, 0.8, 1), (60, 20, 80, 40, 0.7, 2)]))]


@pytest.fixture
def det_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=FakeYOLO))
    FakeYOLO.calls = []
    from app import detector
    return detector


FRAME = np.zeros((480, 640, 3), dtype=np.uint8)


def test_items_only_model_uses_stock_person_tracker(det_module):
    FakeYOLO.our_names = {0: "gloves", 1: "no_gloves", 2: "mask", 3: "no_mask"}
    det = det_module.YoloDetector("weights/best.pt", person_weights="yolo26n.pt")
    assert det.mode == "two-model"
    out = det(FRAME)
    assert [(d.label, d.track_id) for d in out] == [("person", 7), ("no_gloves", None), ("mask", None)]
    # people tracked by the stock model (person class only), items predicted by ours
    assert FakeYOLO.calls == [("yolo26n.pt", "track", [0]), ("weights/best.pt", "predict", None)]


def test_model_with_person_class_tracks_alone(det_module):
    FakeYOLO.our_names = {0: "person", 1: "mask", 2: "no_mask", 3: "gloves", 4: "no_gloves"}
    det = det_module.YoloDetector("weights/best.pt")
    assert det.mode == "single"
    out = det(FRAME)
    # only people keep a track ID
    assert [(d.label, d.track_id) for d in out] == [("person", 3), ("mask", None)]
    assert [c[:2] for c in FakeYOLO.calls] == [("weights/best.pt", "track")]
