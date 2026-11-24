"""Download the public datasets listed in configs/datasets.yaml (YOLO format).

Usage:
    export ROBOFLOW_API_KEY=xxxx
    python scripts/download_datasets.py [--only kitchen-hygiene-gear]
"""
import argparse
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=ROOT / "configs" / "datasets.yaml")
    ap.add_argument("--out", default=ROOT / "data" / "raw")
    ap.add_argument("--format", default="yolov8")
    ap.add_argument("--only", nargs="*", help="dataset names to download")
    args = ap.parse_args()

    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        raise SystemExit("Set ROBOFLOW_API_KEY (free at roboflow.com → Settings → API Keys)")

    from roboflow import Roboflow

    rf = Roboflow(api_key=key)
    cfg = yaml.safe_load(Path(args.config).read_text())
    for ds in cfg["datasets"]:
        if args.only and ds["name"] not in args.only:
            continue
        dest = Path(args.out) / ds["name"]
        print(f"→ {ds['name']} ({ds['workspace']}/{ds['project']} v{ds['version']})")
        try:
            rf.workspace(ds["workspace"]).project(ds["project"]).version(ds["version"]).download(
                args.format, location=str(dest))
        except Exception as e:  # keep going if one dataset/version is unavailable
            print(f"  ! failed: {e}")


if __name__ == "__main__":
    main()
