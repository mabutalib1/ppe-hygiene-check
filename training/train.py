"""Download a Roboflow dataset version, fine-tune YOLO, score on the test videos,
and append a row to results.md (for slides) and results.json (for the dashboard).

    export ROBOFLOW_API_KEY=xxxx
    python training/train.py --workspace our-workspace --project check-hygiene --version 3
    python training/train.py ... --model yolo26s.pt --imgsz 960      # if gloves stay weak
    python training/train.py ... --model yolo11s.pt                  # fallback model
    python training/train.py --data data/public/v0/data.yaml --device 0 --batch 32   # local dataset

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
CLASSES = ["person", "mask", "no_mask", "gloves", "no_gloves"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, help="local data.yaml instead of a Roboflow download")
    ap.add_argument("--workspace")
    ap.add_argument("--project")
    ap.add_argument("--version", type=int)
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

    if args.data:
        data_yaml = args.data.resolve()
        args.dataset_label = data_yaml.parent.name           # e.g. "v0"
    else:
        if not (args.workspace and args.project and args.version):
            raise SystemExit("Give --data, or --workspace, --project and --version")
        key = os.environ.get("ROBOFLOW_API_KEY")
        if not key:
            raise SystemExit("Set ROBOFLOW_API_KEY (never commit it)")
        from roboflow import Roboflow

        rf = Roboflow(api_key=key)
        ds = rf.workspace(args.workspace).project(args.project).version(args.version).download(args.format)
        data_yaml = Path(ds.location) / "data.yaml"
        args.dataset_label = f"v{args.version}"

    from ultralytics import YOLO

    run_name = f"{args.dataset_label}_{Path(args.model).stem}_{args.imgsz}"
    model = YOLO(args.model)
    model.train(
        data=str(data_yaml),
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

    # final score on the held-out TEST videos (never used for tuning).
    # A dataset without a test split (public-only v0) is scored on valid instead.
    import yaml

    split = "test" if "test" in yaml.safe_load(data_yaml.read_text()) else "val"
    if split == "val":
        print("No test split: scoring on valid. These are not our videos, so don't report it as final.")
        args.note = (args.note + " " if args.note else "") + "(scored on valid, not our test videos)"
    # the folder Ultralytics really used (it adds 2, 3, … when run_name already exists)
    weights = Path(model.trainer.save_dir) / "weights"
    best = YOLO(str(weights / "best.pt"))
    m = best.val(data=str(data_yaml), split=split, imgsz=args.imgsz,
                 project=str(HERE / "runs"), name=f"{run_name}_{split}")
    per_class = {m.names[int(c)]: float(ap50) for c, ap50 in zip(m.box.ap_class_index, m.box.ap50)}
    append_result(args, run_name, float(m.box.map50), float(m.box.map), per_class)
    append_json(args, run_name, float(m.box.map50), float(m.box.map), per_class,
                precision=float(m.box.mp), recall=float(m.box.mr))

    if args.export_onnx:
        best.export(format="onnx", imgsz=args.imgsz)
    print(f"\nWeights: {weights / 'best.pt'}")


def append_result(args, run_name, map50, map5095, per_class):
    cols = CLASSES
    row = [str(date.today()), args.dataset_label, Path(args.model).stem, str(args.imgsz),
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
        "dataset": args.dataset_label,
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
