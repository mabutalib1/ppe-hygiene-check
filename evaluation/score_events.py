"""Level 2 evaluation: compare system alerts to hand-written ground truth.

    python evaluation/score_events.py evaluation/ground_truth/events.csv \
        evaluation/out/durations.csv evaluation/out/timelogic.csv evaluation/out/raw.csv

Matching: a ground-truth violation (removed/missing) is caught by the first
unmatched alert for the same clip and item that arrives between EARLY seconds
before and LATE seconds after it. Person labels are not compared (ground truth
says "left"/"right", the system says Person 3), so keep one violation per item
at a time in each clip.

Metrics (goals from the plan):
  events caught   matched / all ground-truth violations      goal ≥ 80%
  false alarms    unmatched alerts per 5 minutes of video    goal < 1
  alert delay     mean seconds from real removal to alert    goal < 5 s
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

ALERT_CHANGES = {"removed", "missing"}


def read_rows(path: Path) -> List[dict]:
    with open(path, newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def alerts(rows: List[dict]) -> List[dict]:
    return [r for r in rows if r["change"] in ALERT_CHANGES]


def score(gt_rows: List[dict], pred_rows: List[dict], total_minutes: float,
          early: float = 1.0, late: float = 10.0) -> Dict[str, float]:
    gt = alerts(gt_rows)
    preds = alerts(pred_rows)
    by_key = defaultdict(list)
    for i, p in enumerate(preds):
        by_key[(p["clip"], p["item"])].append((float(p["time_sec"]), i))
    for v in by_key.values():
        v.sort()

    used, delays = set(), []
    for g in sorted(gt, key=lambda r: float(r["time_sec"])):
        gt_t = float(g["time_sec"])
        for pt, i in by_key[(g["clip"], g["item"])]:
            if i not in used and gt_t - early <= pt <= gt_t + late:
                used.add(i)
                delays.append(pt - gt_t)
                break

    false_alarms = len(preds) - len(used)
    return {
        "gt_events": len(gt),
        "caught": len(delays),
        "caught_pct": 100.0 * len(delays) / len(gt) if gt else 0.0,
        "alerts": len(preds),
        "false_alarms": false_alarms,
        "false_per_5min": 5.0 * false_alarms / total_minutes if total_minutes else 0.0,
        "mean_delay_s": sum(delays) / len(delays) if delays else float("nan"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ground_truth", type=Path)
    ap.add_argument("durations", type=Path, help="clip,duration_s (written by run_events.py)")
    ap.add_argument("predictions", type=Path, nargs="+")
    ap.add_argument("--early", type=float, default=1.0)
    ap.add_argument("--late", type=float, default=10.0)
    args = ap.parse_args()

    gt = read_rows(args.ground_truth)
    minutes = sum(float(r["duration_s"]) for r in read_rows(args.durations)) / 60.0

    print(f"{'run':20s} {'caught':>12s} {'false/5min':>11s} {'delay s':>8s} {'alerts':>7s}")
    for p in args.predictions:
        s = score(gt, read_rows(p), minutes, args.early, args.late)
        print(f"{p.stem:20s} {s['caught']:>4d}/{s['gt_events']:<3d}{s['caught_pct']:>4.0f}% "
              f"{s['false_per_5min']:>11.2f} {s['mean_delay_s']:>8.1f} {s['alerts']:>7d}")
    print(f"\n{minutes:.1f} minutes of video. Goals: caught ≥ 80%, false < 1 per 5 min, delay < 5 s")


if __name__ == "__main__":
    main()
