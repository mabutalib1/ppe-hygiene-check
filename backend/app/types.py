from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

Box = Tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels

# The 9 detector classes (must match training/classes.yaml)
CLASSES = (
    "person",
    "hairnet", "no_hairnet",
    "mask", "no_mask",
    "gloves", "no_gloves",
    "uniform", "no_uniform",
)

# item -> (wearing class, not-wearing class)
ITEMS = {
    "mask": ("mask", "no_mask"),
    "hairnet": ("hairnet", "no_hairnet"),
    "gloves": ("gloves", "no_gloves"),
    "uniform": ("uniform", "no_uniform"),
}
LABEL_TO_ITEM = {lbl: item for item, pair in ITEMS.items() for lbl in pair}


class Obs(str, Enum):
    """What was seen for one item on one person in one frame."""
    WEARING = "wearing"
    NOT_WEARING = "not_wearing"
    NOT_VISIBLE = "not_visible"


class ItemState(str, Enum):
    OK = "ok"
    VIOLATION = "violation"
    UNKNOWN = "unknown"


@dataclass
class Detection:
    label: str
    conf: float
    box: Box
    track_id: Optional[int] = None  # set for tracked people only

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.box
        return (x1 + x2) / 2, (y1 + y2) / 2

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.box
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def intersection(a: Box, b: Box) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)
