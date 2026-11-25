"""Run the full pipeline offline on the event clips and write the alerts it raises.

    python evaluation/run_events.py --clips data/event_clips --weights backend/weights/best.pt \
        --out evaluation/out/timelogic.csv
    python evaluation/run_events.py ... --raw --out evaluation/out/raw.csv   # per-frame baseline

Uses video time (frame index / fps), not wall-clock time, so results are the
same on a slow laptop. Also writes durations.csv next to --out.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import EngineConfig  # noqa: E402
from app.engine import ViolationEngine, raw_config  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv"}


def run_clip(path: Path, weights: str, cfg: EngineConfig, fps: float, imgsz: int, device: str,
             person_weights: str = "yolo26n.pt"):
    import cv2
    from app.detector import YoloDetector

    det = YoloDetector(weights, device, imgsz, person_weights=person_weights)  # fresh tracker per clip
    eng = ViolationEngine(cfg, camera=path.stem)
    cap = cv2.VideoCapture(str(path))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(src_fps / fps))
    rows, idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            t = idx / src_fps
            h, w = frame.shape[:2]
            _, events = eng.update(t, det(frame), (w, h))
            for e in events:
                rows.append({"clip": path.stem, "person": e["person_id"], "item": e["item"],
                             "change": e["change"], "time_sec": round(e["t"], 2)})
        idx += 1
    cap.release()
    return rows, idx / src_fps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", type=Path, required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--raw", action="store_true", help="per-frame alerts, no time logic")
    ap.add_argument("--fps", type=float, default=10.0)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="")
    ap.add_argument("--person-weights", default="yolo26n.pt",
                    help="stock COCO model for people, used when --weights has no person class")
    args = ap.parse_args()

    cfg = raw_config() if args.raw else EngineConfig.from_env()
    clips = sorted(p for p in args.clips.iterdir() if p.suffix.lower() in VIDEO_EXT)
    if not clips:
        raise SystemExit(f"no videos in {args.clips}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    all_rows, durations = [], []
    for c in clips:
        rows, dur = run_clip(c, args.weights, cfg, args.fps, args.imgsz, args.device, args.person_weights)
        print(f"{c.name}: {sum(r['change'] in ('removed', 'missing') for r in rows)} alerts, {dur:.0f}s")
        all_rows += rows
        durations.append({"clip": c.stem, "duration_s": round(dur, 1)})

    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["clip", "person", "item", "change", "time_sec"])
        w.writeheader()
        w.writerows(all_rows)
    with (args.out.parent / "durations.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["clip", "duration_s"])
        w.writeheader()
        w.writerows(durations)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
