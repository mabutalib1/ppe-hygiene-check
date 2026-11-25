"""Build the model-v0 dataset from public Roboflow Universe datasets only.

Downloads every dataset in public_datasets.yaml, remaps it to our 7 classes
(person boxes added with a COCO-pretrained YOLO), removes near-duplicate frames
shared between datasets, merges them and holds out ~10% valid and ~10% test,
split by source video, with every class and every dataset in each held-out split
when possible. It does NOT train: it prints the command to run.

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


def dhash(path: Path, size: int = 8) -> int | None:
    """64-bit difference hash: survives resizing and re-encoding, not flips or crops.
    None if the file can't be read as an image."""
    try:
        from PIL import Image

        with Image.open(path) as im:
            px = im.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS).tobytes()
    except Exception:  # noqa: BLE001
        return None
    bits = 0
    for r in range(size):
        row = px[r * (size + 1):(r + 1) * (size + 1)]
        for c in range(size):
            bits = bits << 1 | (row[c] > row[c + 1])
    return bits


def label_score(img: Path, person_id: int) -> tuple[int, int]:
    """(distinct item classes, item boxes) in an image's labels. Person boxes are
    ignored: they are added automatically to every dataset."""
    lbl = img.parent.parent / "labels" / f"{img.stem}.txt"
    ids = [int(line.split()[0]) for line in lbl.read_text().splitlines() if line.strip()]
    items = [i for i in ids if i != person_id]
    return len(set(items)), len(items)


def dedup(images: list[Path], max_dist: int, person_id: int):
    """Find near-identical frames (dHash distance <= max_dist).

    Across datasets: keep only the copy whose labels cover the most of our classes
    (e.g. mhm's frame with mask boxes beats KitchenHygiene's copy without them).
    Within one dataset: keep both (consecutive frames of one video look alike).
    Either way the two video groups are linked so they end up in the same split.

    Returns (kept images, linked video-key pairs, number dropped)."""
    n_chunks = max_dist + 1                 # pigeonhole: a match shares >= 1 chunk exactly
    bounds = [64 * i // n_chunks for i in range(n_chunks + 1)]

    def chunks(h: int):
        return [(i, h >> bounds[i] & ((1 << (bounds[i + 1] - bounds[i])) - 1))
                for i in range(n_chunks)]

    buckets: dict[tuple, list] = defaultdict(list)
    kept, links, dropped = [], [], 0
    for img in sorted(images, key=lambda p: label_score(p, person_id), reverse=True):
        h = dhash(img)
        if h is None or not 8 <= bin(h).count("1") <= 56:  # unreadable or near-blank: never matched
            kept.append(img)
            continue
        ds = img.stem.split("__", 1)[0]
        matches = {id(o): o for c in chunks(h) for h2, o in buckets[c]
                   if bin(h ^ h2).count("1") <= max_dist}
        links += [(video_key(img.stem), video_key(o.stem)) for o in matches.values()]
        if any(o.stem.split("__", 1)[0] != ds for o in matches.values()):
            dropped += 1
            continue
        kept.append(img)
        for c in chunks(h):
            buckets[c].append((h, img))
    return kept, links, dropped


def group_tags(imgs: list[Path], names: list[str]) -> set[str]:
    """Our classes and source datasets present in one group of images."""
    tags = set()
    for img in imgs:
        tags.add("dataset:" + img.stem.split("__", 1)[0])
        lbl = img.parent.parent / "labels" / f"{img.stem}.txt"
        tags |= {names[int(line.split()[0])] for line in lbl.read_text().splitlines() if line.strip()}
    return tags


def split_groups(groups: dict[str, list[Path]], shares: dict[str, float], seed: int,
                 names: list[str]) -> dict[str, str]:
    """group key -> split name. Held-out splits are filled in order (test, then valid)
    by whole groups: first one group for each class and each dataset the split still
    lacks (rarest first), then random groups up to the share. A group stays in train
    if it would push a split past 1.5x its share (one huge video can't take it over)
    or if it holds the last free group of some class or dataset (train needs it most)."""
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    size = {k: len(v) for k, v in groups.items()}
    tags = {k: group_tags(v, names) for k, v in groups.items()}
    total = sum(size.values())
    where: dict[str, str] = {}
    free = Counter(t for k in keys for t in tags[k])   # groups per tag not yet held out
    for split, share in shares.items():
        if share <= 0:
            continue
        target, n, have = share * total, 0, set()

        def ok(k):
            return (k not in where and n + size[k] <= 1.5 * target
                    and all(free[t] >= 2 for t in tags[k]))

        def take(k):
            nonlocal n, have
            where[k], n, have = split, n + size[k], have | tags[k]
            free.subtract(tags[k])

        for tag in sorted(free, key=lambda t: (free[t], t)):   # rarest first
            if tag in have:
                continue
            k = next((k for k in keys if tag in tags[k] and ok(k)), None)
            if k is None:
                print(f"[{split}] no video group with {tag} can be spared: {split} won't contain it",
                      file=sys.stderr)
                continue
            take(k)
        for k in keys:
            if n >= target:
                break
            if ok(k):
                take(k)
    return {k: where.get(k, "train") for k in keys}


def merge(remapped: list[Path], out: Path, val_share: float, seed: int,
          dedup_dist: int = 3, test_share: float = 0.0) -> dict:
    """Merge remapped datasets into out/{train,valid,test}, split by source video.
    Videos that share a frame (found by dedup) count as one group."""
    if out.exists():
        shutil.rmtree(out)
    names, name_to_id, _ = load_classes()
    images = [img for d in remapped for img in sorted((d / "train" / "images").glob("*"))
              if img.suffix.lower() in IMG_EXT]
    links, dropped = [], 0
    if dedup_dist >= 0:
        images, links, dropped = dedup(images, dedup_dist, name_to_id["person"])
        print(f"dedup: dropped {dropped} cross-dataset duplicates, "
              f"{len(links)} links between video groups")

    parent: dict[str, str] = {}

    def root(k: str) -> str:
        parent.setdefault(k, k)
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for a, b in links:
        parent[root(a)] = root(b)
    groups: dict[str, list[Path]] = defaultdict(list)
    for img in images:
        groups[root(video_key(img.stem))].append(img)

    where = split_groups(groups, {"test": test_share, "valid": val_share}, seed, names)
    counts = {"train": Counter(), "valid": Counter(), "test": Counter()}
    for k, imgs in groups.items():
        split = where[k]
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)
        for img in imgs:
            lbl = img.parent.parent / "labels" / f"{img.stem}.txt"
            shutil.copy2(img, out / split / "images" / img.name)
            shutil.copy2(lbl, out / split / "labels" / lbl.name)
            counts[split]["images"] += 1
            for line in lbl.read_text().splitlines():
                counts[split][names[int(line.split()[0])]] += 1

    data = {"path": str(out.resolve()), "train": "train/images", "val": "valid/images"}
    if counts["test"]["images"]:
        data["test"] = "test/images"    # train.py scores on it when present
    (out / "data.yaml").write_text(yaml.safe_dump({**data, "names": names}, sort_keys=False))
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
    ap.add_argument("--test-share", type=float, default=0.10, help="0 = no test split")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dedup-dist", type=int, default=3,
                    help="max dHash bit difference for two frames to count as duplicates; -1 = off")
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

    counts = merge(remapped, args.out, args.val_share, args.seed, args.dedup_dist, args.test_share)
    names, _, _ = load_classes()
    print(f"\nv0 dataset → {args.out}")
    print(f"{'':12s} {'train':>8s} {'valid':>8s} {'test':>8s}")
    for k in ["images", *names]:
        print(f"{k:12s} {counts['train'][k]:>8d} {counts['valid'][k]:>8d} {counts['test'][k]:>8d}")
    print("\nNothing was trained. When you're ready (RTX 5080, ~45–75 min):\n"
          f"  python training/train.py --data {args.out / 'data.yaml'} --device 0 --batch 32 "
          "--note \"v0 public data only\"")


if __name__ == "__main__":
    main()
