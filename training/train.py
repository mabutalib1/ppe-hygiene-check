"""Download a Roboflow dataset version, fine-tune YOLO, score on the test videos,
and append a row to results.md (for slides) and results.json (for the dashboard).

    export ROBOFLOW_API_KEY=xxxx
    python training/train.py --workspace our-workspace --project check-hygiene --version 3
    python training/train.py ... --model yolo26s.pt --imgsz 960      # if gloves stay weak
    python training/train.py ... --model yolo11s.pt                  # fallback model

Runs best on a GPU (Colab / Kaggle). See train_colab.ipynb.
"""
import argparse
import json
import os
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results.md"
RESULTS_JSON = HERE / "results.json"
CLASSES = ["person", "hairnet", "no_hairnet", "mask", "no_mask", "gloves", "no_gloves"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--version", type=int, required=True)
    ap.add_argument("--format", default="yolov8", help="copy the exact string from Roboflow's export dialog")
    ap.add_argument("--model", default="yolo26s.pt")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--device", default=None)
    ap.add_argument("--export-onnx", action="store_true")
    ap.add_argument("--note", default="", help="what changed in this run")
    args = ap.parse_args()

    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        raise SystemExit("Set ROBOFLOW_API_KEY (never commit it)")

    from roboflow import Roboflow
    from ultralytics import YOLO

    rf = Roboflow(api_key=key)
    ds = rf.workspace(args.workspace).project(args.project).version(args.version).download(args.format)

    run_name = f"v{args.version}_{Path(args.model).stem}_{args.imgsz}"
    model = YOLO(args.model)
    model.train(
        data=f"{ds.location}/data.yaml",
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        device=args.device,
        project=str(HERE / "runs"),
        name=run_name,
        # Roboflow already applied our augmentations; keep YOLO's geometric ones mild
        flipud=0.0,
        degrees=0.0,
    )

    # final score on the held-out TEST videos (never used for tuning)
    best = YOLO(str(HERE / "runs" / run_name / "weights" / "best.pt"))
    m = best.val(data=f"{ds.location}/data.yaml", split="test", imgsz=args.imgsz)
    per_class = {m.names[int(c)]: float(ap50) for c, ap50 in zip(m.box.ap_class_index, m.box.ap50)}
    append_result(args, run_name, float(m.box.map50), float(m.box.map), per_class)
    append_json(args, run_name, float(m.box.map50), float(m.box.map), per_class,
                precision=float(m.box.mp), recall=float(m.box.mr))

    if args.export_onnx:
        best.export(format="onnx", imgsz=args.imgsz)
    print(f"\nWeights: {HERE / 'runs' / run_name / 'weights' / 'best.pt'}")


def append_result(args, run_name, map50, map5095, per_class):
    cols = CLASSES
    row = [str(date.today()), f"v{args.version}", Path(args.model).stem, str(args.imgsz),
           f"{map50:.3f}", f"{map5095:.3f}"] + \
          [f"{per_class[c]:.2f}" if c in per_class else "-" for c in cols] + [args.note or run_name]
    with RESULTS.open("a") as f:
        f.write("| " + " | ".join(row) + " |\n")
    print("Appended to", RESULTS)



def append_json(args, run_name, map50, map5095, per_class, precision, recall):
    runs = json.loads(RESULTS_JSON.read_text()) if RESULTS_JSON.exists() else []
    runs.append({
        "date": str(date.today()),
        "run": run_name,
        "dataset": f"v{args.version}",
        "model": Path(args.model).stem,
        "imgsz": args.imgsz,
        "epochs": args.epochs,
        "map50": round(map50, 4),
        "map50_95": round(map5095, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "per_class": {c: round(per_class[c], 4) for c in CLASSES if c in per_class},
        "note": args.note or run_name,
    })
    RESULTS_JSON.write_text(json.dumps(runs, indent=2) + "\n")
    print("Appended to", RESULTS_JSON)


if __name__ == "__main__":
    main()
