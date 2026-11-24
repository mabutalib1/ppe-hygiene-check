"""Remap a public Roboflow dataset (YOLO export) to our 9 classes, as a TRAIN-ONLY folder.

Public images must never enter valid or test (our test set is our own videos).
Upload the output folder to Roboflow with the split set to "train".

    python training/remap_public.py data/public/kitchen-hygiene-gear out/public_kitchen

Labels whose meaning doesn't match ours are dropped and printed, so check them
and extend `aliases` in classes.yaml only when the meaning really matches.
"""
import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_classes(path=HERE / "classes.yaml"):
    cfg = yaml.safe_load(Path(path).read_text())
    names = cfg["names"]
    return names, {n: i for i, n in enumerate(names)}, {str(k).lower(): v for k, v in cfg["aliases"].items()}


def source_names(ds_dir: Path):
    names = yaml.safe_load((ds_dir / "data.yaml").read_text())["names"]
    return names if isinstance(names, list) else [names[k] for k in sorted(names)]


def build_remap(src_names, aliases, name_to_id):
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
        if parts and remap.get(int(parts[0])) is not None:
            out.append(" ".join([str(remap[int(parts[0])]), *parts[1:]]))
    return "\n".join(out) + ("\n" if out else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path, help="Roboflow YOLO export folder (has data.yaml)")
    ap.add_argument("out", type=Path)
    args = ap.parse_args()

    names, name_to_id, aliases = load_classes()
    remap, dropped = build_remap(source_names(args.src), aliases, name_to_id)
    if dropped:
        print(f"dropping labels with no matching meaning: {dropped}", file=sys.stderr)

    img_out, lbl_out = args.out / "train" / "images", args.out / "train" / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)
    counts, n_img = Counter(), 0
    for split in ("train", "valid", "test"):   # all public splits → our train
        for img in sorted((args.src / split / "images").glob("*")):
            if img.suffix.lower() not in IMG_EXT:
                continue
            lbl = args.src / split / "labels" / f"{img.stem}.txt"
            text = remap_label_text(lbl.read_text(), remap) if lbl.exists() else ""
            if not text:
                continue  # nothing we care about in this image
            stem = f"{args.src.name}__{split}__{img.stem}"
            shutil.copy2(img, img_out / f"{stem}{img.suffix}")
            (lbl_out / f"{stem}.txt").write_text(text)
            n_img += 1
            for line in text.splitlines():
                counts[names[int(line.split()[0])]] += 1

    (args.out / "data.yaml").write_text(yaml.safe_dump({"train": "train/images", "names": names}))
    print(f"{n_img} images → {args.out}")
    for n in names:
        print(f"  {n:12s} {counts[n]}")


if __name__ == "__main__":
    main()
