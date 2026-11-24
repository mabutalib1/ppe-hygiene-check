"""Train the YOLO PPE detector on the merged dataset.

Usage:
    python scripts/train_detector.py --model yolo11n.pt --epochs 100 --imgsz 640
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=ROOT / "data" / "merged" / "data.yaml")
    ap.add_argument("--model", default="yolo11n.pt")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=None)
    ap.add_argument("--name", default="ppe_detector")
    args = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(ROOT / "runs"),
        name=args.name,
        patience=20,
        fliplr=0.5,      # left/right hands are symmetric
        hsv_v=0.4,       # kitchen lighting varies a lot
    )
    metrics = model.val()
    print(metrics.results_dict)


if __name__ == "__main__":
    main()
