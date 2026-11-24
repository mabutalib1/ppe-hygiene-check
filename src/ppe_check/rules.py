"""Turn per-item results into an overall decision for a role."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from .types import ItemResult, Status, Thresholds

DEFAULT_RULES = Path(__file__).resolve().parents[2] / "configs" / "rules.yaml"


def load_rules(path: Path = DEFAULT_RULES) -> Tuple[Dict[str, List[str]], Thresholds]:
    cfg = yaml.safe_load(Path(path).read_text())
    roles = {name: r["required"] for name, r in cfg["roles"].items()}
    t = cfg.get("thresholds", {})
    return roles, Thresholds(passing=t.get("pass", 0.60), review_below=t.get("review_below", 0.40))


def overall_status(results: Dict[str, ItemResult], required: List[str]) -> Tuple[Status, List[str]]:
    """FAIL beats NEEDS_REVIEW beats PASS. NOT_CHECKED items go to the manual list.

    Returns (overall, manual_items).
    """
    manual, statuses = [], []
    for item in required:
        r = results.get(item)
        if r is None or r.status == Status.NOT_CHECKED:
            manual.append(item)
            continue
        statuses.append(r.status)

    if Status.FAIL in statuses:
        return Status.FAIL, manual
    if Status.NEEDS_REVIEW in statuses or not statuses:
        return Status.NEEDS_REVIEW, manual
    return Status.PASS, manual
