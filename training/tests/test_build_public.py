"""build_public_v0.py with fake "downloaded" exports (no network, no model)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_public_v0 as build  # noqa: E402
import remap_public  # noqa: E402


def fake_export(root: Path, name: str, src_names, frames: dict):
    """frames: {image stem: label text}"""
    d = root / name
    for split in ("train",):
        (d / split / "images").mkdir(parents=True)
        (d / split / "labels").mkdir(parents=True)
        for stem, label in frames.items():
            (d / split / "images" / f"{stem}.jpg").write_bytes(b"jpg")
            (d / split / "labels" / f"{stem}.txt").write_text(label)
    (d / "data.yaml").write_text(yaml.safe_dump({"names": src_names}))
    return d


def test_video_key_groups_frames_of_one_video():
    k = build.video_key
    assert k("kitchenhygiene__train__hairr_mp4-32_jpg.rf.ab12cd") == k("kitchenhygiene__valid__hairr_mp4-84_jpg.rf.ff00")
    assert k("kitchenhygiene__train__hairr_mp4-32_jpg.rf.ab12cd") != k("kitchenhygiene__train__noglovee_mp4-3_jpg.rf.aa")
    assert k("face-mask__train__maksssksksss12_png.rf.0a") == "face-mask__maksssksksss"


def test_build_merges_splits_by_video_and_adds_person(tmp_path, monkeypatch, capsys):
    public = tmp_path / "public"
    kh_names = ["apron", "gloves", "hairnet", "no_gloves", "no_hairnet", "rat"]
    frames = {}
    for vid in ("hairr_mp4", "noglovee_mp4", "kitch_mp4", "cam2_mp4"):
        for i in range(5):
            frames[f"{vid}-{i}_jpg.rf.{i:04x}"] = "2 0.5 0.2 0.1 0.1\n3 0.3 0.6 0.05 0.05\n"
    frames["rat_photo_jpg.rf.beef"] = "5 0.5 0.5 0.2 0.2\n"  # pest only → dropped
    fake_export(public, "kitchenhygiene", kh_names, frames)
    fake_export(public, "face-mask", ["mask_weared_incorrect", "with_mask", "without_mask"],
                {f"maksssksksss{i}_png.rf.{i:04x}": "1 0.5 0.4 0.2 0.2\n0 0.6 0.4 0.2 0.2\n" for i in range(4)})

    cfg = tmp_path / "datasets.yaml"
    cfg.write_text(yaml.safe_dump({"datasets": [{"name": "kitchenhygiene"}, {"name": "face-mask"}]}))
    monkeypatch.setattr(build, "PUBLIC", public)
    monkeypatch.setattr(remap_public, "make_person_detector",
                        lambda m, c, pid: (lambda img: [f"{pid} 0.5 0.5 0.4 0.9"]))
    out = tmp_path / "v0"
    monkeypatch.setattr(sys, "argv", ["build_public_v0.py", "--skip-download", "--config", str(cfg),
                                      "--out", str(out), "--val-share", "0.2", "--test-share", "0.2"])
    build.main()

    data = yaml.safe_load((out / "data.yaml").read_text())
    assert data["train"] == "train/images" and data["val"] == "valid/images" and len(data["names"]) == 5
    assert data["test"] == "test/images"
    split = {s: {p.stem for p in (out / s / "images").glob("*")} for s in ("train", "valid", "test")}
    assert sum(map(len, split.values())) == 24 and all(split.values())  # rat photo dropped
    # no image and no video in two splits
    for a, b in (("train", "valid"), ("train", "test"), ("valid", "test")):
        assert not (split[a] & split[b])
        assert not ({build.video_key(s) for s in split[a]} & {build.video_key(s) for s in split[b]})
    # every image got a person box; the mask set mapped to mask / no_mask
    for lbl in (out / "train" / "labels").glob("*.txt"):
        assert any(line.startswith("0 ") for line in lbl.read_text().splitlines())
    out_text = capsys.readouterr()
    assert "Nothing was trained" in out_text.out
    assert "never labels ['mask', 'no_mask']" in out_text.err  # kitchenhygiene gap is reported


def noise_image(path: Path, seed: int):
    import random

    from PIL import Image

    rnd = random.Random(seed)
    Image.frombytes("L", (32, 32), bytes(rnd.randrange(256) for _ in range(32 * 32))).save(path)


def remapped_dir(root: Path, name: str, frames: dict) -> Path:
    """frames: {stem: (image seed, label text)}, laid out like remap_dataset's output."""
    d = root / name
    (d / "train" / "images").mkdir(parents=True)
    (d / "train" / "labels").mkdir(parents=True)
    for stem, (seed, label) in frames.items():
        noise_image(d / "train" / "images" / f"{name}__train__{stem}.png", seed)
        (d / "train" / "labels" / f"{name}__train__{stem}.txt").write_text(label)
    return d


def test_dedup_keeps_richest_copy_and_links_videos(tmp_path):
    # mhm's copy of KitchenHygiene frame 0 also has a mask box → it wins
    kh = remapped_dir(tmp_path, "kitchenhygiene", {
        f"hairr_mp4-{i}_jpg": (i, "0 0.5 0.5 0.4 0.9\n3 0.5 0.6 0.1 0.1\n") for i in range(3)})
    mhm = remapped_dir(tmp_path, "mhm-kitchen", {
        "maskclip_mp4-0_jpg": (0, "0 0.5 0.5 0.4 0.9\n3 0.5 0.6 0.1 0.1\n1 0.5 0.3 0.1 0.1\n"),
        "maskclip_mp4-1_jpg": (10, "1 0.5 0.3 0.1 0.1\n")})
    images = sorted((kh / "train" / "images").glob("*")) + sorted((mhm / "train" / "images").glob("*"))

    kept, links, dropped = build.dedup(images, 3, person_id=0)
    stems = {p.stem for p in kept}
    assert dropped == 1 and len(kept) == 4
    assert "kitchenhygiene__train__hairr_mp4-0_jpg" not in stems
    assert "mhm-kitchen__train__maskclip_mp4-0_jpg" in stems
    assert ("kitchenhygiene__hairr_mp4", "mhm-kitchen__maskclip_mp4") in links

    # the two linked videos land in the same split, whatever the seed
    for seed in range(5):
        out = tmp_path / f"out{seed}"
        build.merge([kh, mhm], out, val_share=0.5, seed=seed)
        split_of = {p.stem: s for s in ("train", "valid") for p in (out / s / "images").glob("*")}
        assert len(split_of) == 4
        assert len(set(split_of.values())) == 1


def test_split_puts_every_class_and_dataset_in_every_split(tmp_path):
    # 20 common gloves-only videos, 3 rare no_mask videos, 3 videos from a small no_gloves dataset
    frames = {f"g{i}_mp4-{j}_jpg": (100 * i + j, "3 0.5 0.5 0.1 0.1\n") for i in range(20) for j in range(5)}
    frames |= {f"nm{i}_mp4-{j}_jpg": (5000 + 10 * i + j, "2 0.5 0.5 0.1 0.1\n") for i in range(3) for j in range(5)}
    big = remapped_dir(tmp_path, "big", frames)
    small = remapped_dir(tmp_path, "small", {
        f"s{i}_mp4-{j}_jpg": (9000 + 10 * i + j, "4 0.5 0.5 0.1 0.1\n") for i in range(3) for j in range(5)})

    for seed in range(5):
        out = tmp_path / f"out{seed}"
        counts = build.merge([big, small], out, val_share=0.1, seed=seed, test_share=0.1)
        assert sum(counts[s]["images"] for s in counts) == 130
        for s in ("train", "valid", "test"):
            assert counts[s]["no_mask"] and counts[s]["gloves"] and counts[s]["no_gloves"], (seed, s)
            assert {p.stem.split("__")[0] for p in (out / s / "images").glob("*")} == {"big", "small"}
        for s in ("valid", "test"):
            assert counts[s]["images"] <= 1.5 * 0.1 * 130


def test_split_never_takes_trains_only_group(tmp_path, capsys):
    # one no_mask video only: it must stay in train, and the build says so
    frames = {f"g{i}_mp4-{j}_jpg": (100 * i + j, "3 0.5 0.5 0.1 0.1\n") for i in range(10) for j in range(5)}
    frames |= {f"nm_mp4-{j}_jpg": (5000 + j, "2 0.5 0.5 0.1 0.1\n") for j in range(5)}
    d = remapped_dir(tmp_path, "big", frames)
    counts = build.merge([d], tmp_path / "out", val_share=0.1, seed=0, test_share=0.1)
    assert counts["train"]["no_mask"] == 5 and not counts["test"]["no_mask"]
    assert "[test] no video group with no_mask can be spared" in capsys.readouterr().err


def test_dedup_off_keeps_everything(tmp_path):
    a = remapped_dir(tmp_path, "a", {"v_mp4-0_jpg": (0, "1 0.5 0.5 0.1 0.1\n")})
    b = remapped_dir(tmp_path, "b", {"w_mp4-0_jpg": (0, "1 0.5 0.5 0.1 0.1\n")})
    counts = build.merge([a, b], tmp_path / "out", val_share=0.0, seed=0, dedup_dist=-1)
    assert counts["train"]["images"] == 2


def test_requires_key_without_skip(tmp_path, monkeypatch):
    monkeypatch.delenv("ROBOFLOW_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["build_public_v0.py"])
    try:
        build.main()
    except SystemExit as e:
        assert "ROBOFLOW_API_KEY" in str(e)
    else:
        raise AssertionError("should stop without a key")
