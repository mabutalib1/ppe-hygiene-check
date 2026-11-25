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
                                      "--out", str(out), "--val-share", "0.2"])
    build.main()

    data = yaml.safe_load((out / "data.yaml").read_text())
    assert data["train"] == "train/images" and data["val"] == "valid/images" and len(data["names"]) == 7
    train = {p.stem for p in (out / "train" / "images").glob("*")}
    valid = {p.stem for p in (out / "valid" / "images").glob("*")}
    assert len(train) + len(valid) == 24 and valid and not (train & valid)  # rat photo dropped
    # no video is split across train and valid
    assert not ({build.video_key(s) for s in train} & {build.video_key(s) for s in valid})
    # every image got a person box; the mask set mapped to mask / no_mask
    for lbl in (out / "train" / "labels").glob("*.txt"):
        assert any(line.startswith("0 ") for line in lbl.read_text().splitlines())
    out_text = capsys.readouterr()
    assert "Nothing was trained" in out_text.out
    assert "never labels ['mask', 'no_mask']" in out_text.err  # kitchenhygiene gap is reported


def test_requires_key_without_skip(tmp_path, monkeypatch):
    monkeypatch.delenv("ROBOFLOW_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["build_public_v0.py"])
    try:
        build.main()
    except SystemExit as e:
        assert "ROBOFLOW_API_KEY" in str(e)
    else:
        raise AssertionError("should stop without a key")
