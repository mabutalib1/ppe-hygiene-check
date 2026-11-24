"""Read the project's result files for the dashboard.

Each reader returns an "empty" shape when its file doesn't exist yet, so the
dashboard can show a clear "not run yet" state instead of an error:

- training/results.json      appended by training/train.py (one entry per run)
- evaluation/results.json    written by evaluation/score_events.py --json
- data/recording_log.csv     filled in by hand while recording
"""
from __future__ import annotations

import csv
import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

log = logging.getLogger("check.results")

CREDENTIALS = re.compile(r"(?<=://)[^/@\s]+@")


def redact_source(source: str) -> str:
    """rtsp://user:pass@host/... → rtsp://***@host/... (never send camera passwords out)."""
    return CREDENTIALS.sub("***@", source)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as e:
        log.warning("could not read %s: %s", path, e)
        return default


def training_results(path: Path) -> dict:
    runs = _read_json(path, [])
    if not isinstance(runs, list):
        runs = []
    return {"runs": runs}


def evaluation_results(path: Path) -> dict:
    data = _read_json(path, None)
    if not isinstance(data, dict):
        return {"runs": [], "generated_at": None, "minutes": None}
    data.setdefault("runs", [])
    return data


def dataset_summary(path: Path) -> dict:
    """Counts from the recording log: clips per split, per clip type, per angle."""
    rows = []
    if path.exists():
        with path.open(newline="") as f:
            rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k}
                    for r in csv.DictReader(f)]
        rows = [r for r in rows if r.get("file")]
    count = lambda key: dict(Counter(r.get(key) or "?" for r in rows))  # noqa: E731
    return {
        "clips": len(rows),
        "by_split": count("split"),
        "by_type": count("clip_type"),
        "by_angle": count("angle"),
        "by_lighting": count("lighting"),
    }
