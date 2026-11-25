"""Overlay: person boxes coloured by their worst item state, with ID and item icons."""
from __future__ import annotations

from typing import Dict, List

import cv2
import numpy as np

from .types import Detection

# BGR
COLORS = {"ok": (80, 200, 80), "violation": (40, 40, 230), "unknown": (150, 150, 150)}
SHORT = {"mask": "M", "gloves": "G"}


def _worst(items: Dict[str, str]) -> str:
    if "violation" in items.values():
        return "violation"
    if items and all(v == "ok" for v in items.values()):
        return "ok"
    return "unknown"


def annotate(frame: np.ndarray, detections: List[Detection], status: List[dict],
             track_to_pid: Dict[int, int]) -> np.ndarray:
    img = frame.copy()
    by_pid = {s["id"]: s["items"] for s in status}
    for d in detections:
        if d.label != "person" or d.track_id is None:
            continue
        pid = track_to_pid.get(d.track_id)
        items = by_pid.get(pid, {})
        color = COLORS[_worst(items)]
        x1, y1, x2, y2 = map(int, d.box)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        label = f"Person {pid}"
        cv2.rectangle(img, (x1, max(0, y1 - 28)), (x1 + 12 * len(label) + 10, y1), color, -1)
        cv2.putText(img, label, (x1 + 5, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        # item chips under the label
        for i, (item, state) in enumerate(items.items()):
            cx = x1 + 5 + i * 30
            cv2.rectangle(img, (cx, y1 + 5), (cx + 25, y1 + 30), COLORS[state], -1)
            cv2.putText(img, SHORT[item], (cx + 6, y1 + 24), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (255, 255, 255), 2)
    return img
