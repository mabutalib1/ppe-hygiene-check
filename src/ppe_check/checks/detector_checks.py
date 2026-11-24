"""Phase 1 checks driven directly by the YOLO detector."""
from __future__ import annotations

from typing import Iterable, List

from ..types import Detection, ItemResult, Status, Thresholds


def _best(dets: List[Detection], labels: Iterable[str]):
    cands = [d for d in dets if d.label in labels]
    return max(cands, key=lambda d: d.conf) if cands else None


def _binary_check(item, dets, pos, negs, th: Thresholds) -> ItemResult:
    """Generic present/absent check: the most confident relevant label wins."""
    best = _best(dets, (pos, *negs))
    if best is None:
        return ItemResult(item, Status.NEEDS_REVIEW, 0.0, f"no {item} evidence detected")
    if best.conf < th.review_below:
        return ItemResult(item, Status.NEEDS_REVIEW, best.conf,
                          f"low confidence ({best.label})", best.box)
    if best.conf < th.passing:
        return ItemResult(item, Status.NEEDS_REVIEW, best.conf,
                          f"uncertain ({best.label})", best.box)
    if best.label == pos:
        return ItemResult(item, Status.PASS, best.conf, best.label, best.box)
    return ItemResult(item, Status.FAIL, best.conf, best.label, best.box)


def check_facemask(dets: List[Detection], th: Thresholds) -> ItemResult:
    return _binary_check("facemask", dets, "mask", ("no_mask", "incorrect_mask"), th)


def check_hairnet(dets: List[Detection], th: Thresholds) -> ItemResult:
    return _binary_check("hairnet", dets, "hairnet", ("no_hairnet",), th)


def check_gloves(dets: List[Detection], th: Thresholds) -> ItemResult:
    """Both hands must be gloved; any confident bare hand fails."""
    bare = [d for d in dets if d.label == "bare_hand" and d.conf >= th.passing]
    if bare:
        b = max(bare, key=lambda d: d.conf)
        return ItemResult("gloves", Status.FAIL, b.conf, "bare hand detected", b.box)

    gloves = sorted((d for d in dets if d.label == "glove" and d.conf >= th.passing),
                    key=lambda d: d.conf, reverse=True)
    if len(gloves) >= 2:
        return ItemResult("gloves", Status.PASS, gloves[1].conf, "2 gloved hands", gloves[0].box)
    if len(gloves) == 1:
        return ItemResult("gloves", Status.NEEDS_REVIEW, gloves[0].conf,
                          "only 1 gloved hand visible", gloves[0].box)
    return ItemResult("gloves", Status.NEEDS_REVIEW, 0.0, "no hands detected")
