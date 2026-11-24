"""Merge Roboflow YOLO exports in data/raw/* into one dataset with unified classes.

Each source's labels are remapped through configs/classes.yaml `aliases`;
unknown labels are dropped (and reported) so you can extend the alias map.

Usage:
    python scripts/merge_datasets.py [--raw data/raw] [--out data/merged]
"""
import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPLITS = {"train": "train", "valid": "val", "val": "val", "test": "test"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_unified(path):
    cfg = yaml.safe_load(Path(path).read_text())
    classes = {int(k): v for k, v in cfg["classes"].items()}
    name_to_id = {v: k for k, v in classes.items()}
    aliases = {str(k).lower(): v for k, v in cfg["aliases"].items()}
    return classes, name_to_id, aliases


def source_names(ds_dir: Path):
    names = yaml.safe_load((ds_dir / "data.yaml").read_text())["names"]
    return names if isinstance(names, list) else [names[k] for k in sorted(names)]


def build_remap(src_names, aliases, name_to_id):
    """source class index -> unified class index (or None to drop)."""
    remap, dropped = {}, []
    for i, n in enumerate(src_names):
        target = aliases.get(str(n).lower().strip())
        remap[i] = name_to_id[target] if target else None
        if target is None:
            dropped.append(n)
    return remap, dropped


def remap_label_text(text: str, remap) -> str:
    out = []
    for line in text.strip().splitlines():
        parts = line.split()
        if not parts:
            continue
        new = remap.get(int(parts[0]))
        if new is not None:
            out.append(" ".join([str(new), *parts[1:]]))
    return "\n".join(out) + ("\n" if out else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=ROOT / "data" / "raw")
    ap.add_argument("--out", default=ROOT / "data" / "merged")
    ap.add_argument("--classes", default=ROOT / "configs" / "classes.yaml")
    args = ap.parse_args()

    classes, name_to_id, aliases = load_unified(args.classes)
    raw, out = Path(args.raw), Path(args.out)
    if out.exists():
        shutil.rmtree(out)

    counts = Counter()
    for ds_dir in sorted(p for p in raw.iterdir() if (p / "data.yaml").exists()):
        remap, dropped = build_remap(source_names(ds_dir), aliases, name_to_id)
        if dropped:
            print(f"[{ds_dir.name}] dropping unmapped labels: {dropped}", file=sys.stderr)
        for src_split, dst_split in SPLITS.items():
            img_dir = ds_dir / src_split / "images"
            if not img_dir.exists():
                continue
            (out / "images" / dst_split).mkdir(parents=True, exist_ok=True)
            (out / "labels" / dst_split).mkdir(parents=True, exist_ok=True)
            for img in img_dir.iterdir():
                if img.suffix.lower() not in IMG_EXT:
                    continue
                stem = f"{ds_dir.name}__{img.stem}"
                lbl = ds_dir / src_split / "labels" / f"{img.stem}.txt"
                text = remap_label_text(lbl.read_text(), remap) if lbl.exists() else ""
                shutil.copy2(img, out / "images" / dst_split / f"{stem}{img.suffix}")
                (out / "labels" / dst_split / f"{stem}.txt").write_text(text)
                for line in text.splitlines():
                    counts[classes[int(line.split()[0])]] += 1

    data_yaml = {
        "path": str(out.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": classes,
    }
    (out / "data.yaml").write_text(yaml.safe_dump(data_yaml, sort_keys=False))
    print("Instances per class:")
    for name in classes.values():
        print(f"  {name:15s} {counts[name]}")
    print(f"Wrote {out / 'data.yaml'}")


if __name__ == "__main__":
    main()
