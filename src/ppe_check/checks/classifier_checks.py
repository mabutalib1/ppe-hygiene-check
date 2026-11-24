"""Phase 2/3 checks that need custom data. Stubs until models are trained.

Each returns NOT_CHECKED so the report lists the item for manual inspection
instead of pretending it passed.

Plan:
  hair    → crop head (above face / hairnet box) → classifier: covered / exposed
  uniform → crop torso from person box → embedding (e.g. CLIP/DINOv2) →
            cosine similarity vs venue reference photos
  nails   → MediaPipe hand landmarks → fingertip crops → classifier:
            ok / long / polish / dirty   (check-in close-up only)
"""
from __future__ import annotations

from ..types import ItemResult, Status


def check_hair(frame, dets, th) -> ItemResult:
    return ItemResult("hair", Status.NOT_CHECKED, reason="hair classifier not trained yet (phase 2)")


def check_uniform(frame, dets, th) -> ItemResult:
    return ItemResult("uniform", Status.NOT_CHECKED, reason="uniform matcher not built yet (phase 2)")


def check_nails(frame, dets, th) -> ItemResult:
    return ItemResult("nails", Status.NOT_CHECKED, reason="nails classifier not trained yet (phase 3)")
