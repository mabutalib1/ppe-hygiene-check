"""Build the model-v0 dataset from public Roboflow Universe datasets only.

Downloads every dataset in public_datasets.yaml, remaps it to our 7 classes
(person boxes added with a COCO-pretrained YOLO), merges them and holds out
~10% as a validation split. It does NOT train: it prints the command to run.

    export ROBOFLOW_API_KEY=xxxx               # never commit it
    python training/build_public_v0.py         # download + remap + merge
    python training/build_public_v0.py --skip-download   # reuse data/public/<name>/

Output: data/public/v0/data.yaml (gitignored, like all footage and images).

v0 is a starting point, not the final model: its validation images are public
frames, not our videos, so its scores say little about our kitchen. Use v0 to
pre-label our own frames (Roboflow Label Assist), then train v1 with our data.
"""
from __future__ import annotations

import argparse
import os
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from remap_public import IMG_EXT, load_classes, remap_dataset  # noqa: E402

PUBLIC = ROOT / "data" / "public"
YOLO_FORMAT = "yolov8"  # same label format YOLO26 trains on


def video_key(stem: str) -> str:
    """Group frames of the same source video so they land in the same split.
    'kitchenhygiene__train__hairr_mp4-32_jpg.rf.ab12' → 'kitchenhygiene__hairr_mp4'"""
    ds, _, rest = stem.split("__", 2) if stem.count("__") >= 2 else ("", "", stem)
    rest = re.sub(r"\.rf\.[0-9a-f]+$", "", rest)        # Roboflow hash
    rest = re.sub(r"_(jpe?g|png|bmp|webp)$", "", rest)   # extension folded into the name
    rest = re.sub(r"[-_ ]?\(?\d+\)?$", "", rest)         # trailing frame number
    return f"{ds}__{rest or stem}"


def download(cfg: dict, dest: Path, api_key: str) -> Path:
    from roboflow import Roboflow

    project = Roboflow(api_key=api_key).workspace(cfg["workspace"]).project(cfg["project"])
    version = cfg.get("version")
    if version is None:
        try:
            version = max(int(str(v.version).rstrip("/").split("/")[-1]) for v in project.versions())
        except Exception as e:  # noqa: BLE001
            raise SystemExit(f"{cfg['name']}: could not find the newest version ({e}). "
                             f"Set 'version' in public_datasets.yaml.") from e
    print(f"downloading {cfg['name']} v{version} …")
    project.version(version).download(YOLO_FORMAT, location=str(dest), overwrite=True)
    return dest


def merge(remapped: list[Path], out: Path, val_share: float, seed: int) -> dict:
    """Merge remapped datasets into out/{train,valid}, split by source video."""
    if out.exists():
        shutil.rmtree(out)
    groups: dict[str, list[Path]] = defaultdict(list)
    for d in remapped:
        for img in (d / "train" / "images").glob("*"):
            if img.suffix.lower() in IMG_EXT:
                groups[video_key(img.stem)].append(img)

    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    total = sum(len(v) for v in groups.values())
    val_keys, n_val = set(), 0
    for k in keys:                      # fill valid by whole videos up to ~val_share
        if n_val >= val_share * total:
            break
        val_keys.add(k)
        n_val += len(groups[k])

    names, _, _ = load_classes()
    counts = {"train": Counter(), "valid": Counter()}
    for k, imgs in groups.items():
        split = "valid" if k in val_keys else "train"
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)
        for img in imgs:
            lbl = img.parent.parent / "labels" / f"{img.stem}.txt"
            shutil.copy2(img, out / split / "images" / img.name)
            shutil.copy2(lbl, out / split / "labels" / lbl.name)
            counts[split]["images"] += 1
            for line in lbl.read_text().splitlines():
                counts[split][names[int(line.split()[0])]] += 1

    (out / "data.yaml").write_text(yaml.safe_dump({
        "path": str(out.resolve()),
        "train": "train/images",
        "val": "valid/images",
        "names": names,
    }, sort_keys=False))
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=HERE / "public_datasets.yaml")
    ap.add_argument("--only", nargs="*", help="dataset names to include (default: all)")
    ap.add_argument("--skip-download", action="store_true", help="reuse data/public/<name>/")
    ap.add_argument("--no-person", action="store_true", help="don't add person boxes (not recommended)")
    ap.add_argument("--person-model", default="yolo26n.pt")
    ap.add_argument("--person-conf", type=float, default=0.40)
    ap.add_argument("--val-share", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=PUBLIC / "v0")
    args = ap.parse_args()

    datasets = yaml.safe_load(args.config.read_text())["datasets"]
    if args.only:
        datasets = [d for d in datasets if d["name"] in args.only]
    if not datasets:
        raise SystemExit("no datasets selected")

    key = os.environ.get("ROBOFLOW_API_KEY")
    if not args.skip_download and not key:
        raise SystemExit("Set ROBOFLOW_API_KEY (never commit it), or use --skip-download")

    remapped = []
    for d in datasets:
        src = PUBLIC / d["name"]
        if not args.skip_download:
            download(d, src, key)
        elif not (src / "data.yaml").exists():
            raise SystemExit(f"{src} has no data.yaml: download it first (drop --skip-download)")
        dst = PUBLIC / "_remapped" / d["name"]
        if dst.exists():
            shutil.rmtree(dst)
        n, counts, missing = remap_dataset(src, dst, add_person=not args.no_person,
                                           person_model=args.person_model, person_conf=args.person_conf)
        kept = ", ".join(f"{k} {v}" for k, v in counts.items() if v)
        print(f"{d['name']}: {n} images kept ({kept})")
        remapped.append(dst)

    counts = merge(remapped, args.out, args.val_share, args.seed)
    names, _, _ = load_classes()
    print(f"\nv0 dataset → {args.out}")
    print(f"{'':12s} {'train':>8s} {'valid':>8s}")
    for k in ["images", *names]:
        print(f"{k:12s} {counts['train'][k]:>8d} {counts['valid'][k]:>8d}")
    print("\nNothing was trained. When you're ready (RTX 5080, ~45–75 min):\n"
          f"  python training/train.py --data {args.out / 'data.yaml'} --device 0 --batch 32 "
          "--note \"v0 public data only\"")


if __name__ == "__main__":
    main()
