"""Remap a public Roboflow dataset (YOLO export) to our 7 classes, as a TRAIN-ONLY folder.

Public images must never enter valid or test (our test set is our own videos).
Upload the output folder to Roboflow with the split set to "train".

    python training/remap_public.py data/public/kitchenhygiene out/public_kitchen --add-person

Labels whose meaning doesn't match ours are dropped and printed, so check them
and extend `aliases` in classes.yaml only when the meaning really matches.
Images left with no label of ours (e.g. pest-only photos) are skipped.

MISSING LABELS: if a public dataset doesn't label one of our classes, the people
or masks in its images look like background to the model and it learns to
ignore them. The script lists those classes. Fill them in before training:
  --add-person   labels people with a stock COCO-pretrained YOLO (reliable)
  other classes  label with our own model v1 / Roboflow Label Assist, then review
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


def missing_classes(remap, names):
    """Our classes that no label in the public dataset maps to."""
    have = {v for v in remap.values() if v is not None}
    return [n for i, n in enumerate(names) if i not in have]


def make_person_detector(model_name: str, conf: float, person_id: int):
    """image path -> YOLO label lines for every person a COCO-pretrained model sees."""
    from ultralytics import YOLO

    model = YOLO(model_name)
    coco_person = next(k for k, v in model.names.items() if v == "person")

    def detect(img_path: Path):
        r = model.predict(str(img_path), conf=conf, classes=[coco_person], verbose=False)[0]
        return [f"{person_id} " + " ".join(f"{v:.6f}" for v in box)
                for box in r.boxes.xywhn.tolist()]

    return detect


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
    ap.add_argument("--add-person", action="store_true",
                    help="label people with a COCO-pretrained YOLO when the dataset has no person class")
    ap.add_argument("--person-model", default="yolo26n.pt")
    ap.add_argument("--person-conf", type=float, default=0.40)
    args = ap.parse_args()

    n_img, counts, _ = remap_dataset(args.src, args.out, args.add_person,
                                     args.person_model, args.person_conf)
    print(f"{n_img} images → {args.out}")
    for n, c in counts.items():
        print(f"  {n:12s} {c}")


def remap_dataset(src: Path, out: Path, add_person: bool = False,
                  person_model: str = "yolo26n.pt", person_conf: float = 0.40):
    """Remap one YOLO export into out/train. Returns (images kept, box counts, missing classes)."""
    names, name_to_id, aliases = load_classes()
    remap, dropped = build_remap(source_names(src), aliases, name_to_id)
    if dropped:
        print(f"[{src.name}] dropping labels with no matching meaning: {dropped}", file=sys.stderr)

    missing = missing_classes(remap, names)
    detect_person = None
    if "person" in missing and add_person:
        detect_person = make_person_detector(person_model, person_conf, name_to_id["person"])
        missing.remove("person")
        print(f"[{src.name}] adding person boxes with {person_model} (conf ≥ {person_conf})",
              file=sys.stderr)
    if missing:
        print(f"[{src.name}] WARNING: this dataset never labels {missing}. In its images those "
              f"look like background. Label them before training"
              f"{' (or rerun with --add-person)' if 'person' in missing else ''}.", file=sys.stderr)

    img_out, lbl_out = out / "train" / "images", out / "train" / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)
    counts, n_img = Counter(), 0
    for split in ("train", "valid", "test"):   # all public splits → our train
        for img in sorted((src / split / "images").glob("*")):
            if img.suffix.lower() not in IMG_EXT:
                continue
            lbl = src / split / "labels" / f"{img.stem}.txt"
            text = remap_label_text(lbl.read_text(), remap) if lbl.exists() else ""
            if not text:
                continue  # nothing we care about in this image
            if detect_person:
                text += "".join(f"{line}\n" for line in detect_person(img))
            stem = f"{src.name}__{split}__{img.stem}"
            shutil.copy2(img, img_out / f"{stem}{img.suffix}")
            (lbl_out / f"{stem}.txt").write_text(text)
            n_img += 1
            for line in text.splitlines():
                counts[names[int(line.split()[0])]] += 1

    (out / "data.yaml").write_text(yaml.safe_dump({"train": "train/images", "names": names}))
    return n_img, {n: counts[n] for n in names}, missing

if __name__ == "__main__":
    main()
