from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Tuple

Box = Tuple[float, float, float, float]  # x1, y1, x2, y2 (pixels)

ITEMS = ("nails", "hair", "facemask", "hairnet", "gloves", "uniform")


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_CHECKED = "NOT_CHECKED"  # item not automated yet → manual check


@dataclass
class Detection:
    label: str
    conf: float
    box: Box

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.box
        return (x1 + x2) / 2, (y1 + y2) / 2

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.box
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)


@dataclass
class ItemResult:
    item: str
    status: Status
    confidence: float = 0.0
    reason: str = ""
    evidence_box: Optional[Box] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Thresholds:
    passing: float = 0.60
    review_below: float = 0.40


@dataclass
class Report:
    employee_id: str
    role: str
    timestamp: str
    overall: Status
    items: dict = field(default_factory=dict)  # item -> ItemResult
    manual_items: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "employee_id": self.employee_id,
            "role": self.role,
            "timestamp": self.timestamp,
            "overall": self.overall.value,
            "items": {k: v.to_dict() for k, v in self.items.items()},
            "manual_items": self.manual_items,
        }
