"""Match PPE detections to the employee being checked."""
from __future__ import annotations

from typing import List, Optional

from .types import Box, Detection


def main_person(detections: List[Detection]) -> Optional[Detection]:
    """At a check-in station the employee is the largest person in frame."""
    people = [d for d in detections if d.label == "person"]
    return max(people, key=lambda d: d.area) if people else None


def _inside(point, box: Box, margin: float = 0.10) -> bool:
    x, y = point
    x1, y1, x2, y2 = box
    mx, my = (x2 - x1) * margin, (y2 - y1) * margin
    return (x1 - mx) <= x <= (x2 + mx) and (y1 - my) <= y <= (y2 + my)


def detections_for_person(detections: List[Detection]) -> List[Detection]:
    """Keep PPE detections whose center falls inside the main person's box.

    If no person is detected (e.g. a close-up hands frame) all detections are kept.
    """
    person = main_person(detections)
    ppe = [d for d in detections if d.label != "person"]
    if person is None:
        return ppe
    return [d for d in ppe if _inside(d.center, person.box)]
