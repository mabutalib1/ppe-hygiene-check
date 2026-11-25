"""remap_public.py on a fake KitchenHygiene-style export (no model download)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import remap_public  # noqa: E402

SRC_NAMES = ["apron", "cockroach", "gloves", "hairnet", "lizard",
             "no_apron", "no_gloves", "no_hairnet", "rat"]


def make_export(root: Path) -> Path:
    src = root / "kitchenhygiene"
    (src / "train" / "images").mkdir(parents=True)
    (src / "train" / "labels").mkdir(parents=True)
    (src / "data.yaml").write_text(yaml.safe_dump({"names": SRC_NAMES}))
    files = {
        "worker": "3 0.5 0.2 0.1 0.1\n6 0.3 0.6 0.05 0.05\n0 0.5 0.5 0.3 0.4\n",  # hairnet, no_gloves, apron
        "rat_only": "8 0.5 0.5 0.2 0.2\n",                                     # pest → skipped
        "apron_only": "0 0.5 0.5 0.3 0.4\n",                                   # nothing of ours → skipped
    }
    for stem, label in files.items():
        (src / "train" / "images" / f"{stem}.jpg").write_bytes(b"jpg")
        (src / "train" / "labels" / f"{stem}.txt").write_text(label)
    return src


def run(monkeypatch, src, out, *extra):
    monkeypatch.setattr(sys, "argv", ["remap_public.py", str(src), str(out), *extra])
    remap_public.main()


def test_remap_drops_pests_and_warns_about_missing_classes(tmp_path, monkeypatch, capsys):
    src, out = make_export(tmp_path), tmp_path / "out"
    run(monkeypatch, src, out)
    labels = sorted((out / "train" / "labels").glob("*.txt"))
    assert [p.stem for p in labels] == ["kitchenhygiene__train__worker"]
    names = yaml.safe_load((Path(remap_public.HERE) / "classes.yaml").read_text())["names"]
    got = [names[int(line.split()[0])] for line in labels[0].read_text().splitlines()]
    assert got == ["no_gloves"]  # apron and hairnet dropped
    err = capsys.readouterr().err
    assert "never labels ['person', 'mask', 'no_mask']" in err and "--add-person" in err


def test_add_person_appends_boxes(tmp_path, monkeypatch, capsys):
    src, out = make_export(tmp_path), tmp_path / "out"
    seen = []

    def fake_factory(model, conf, person_id):
        assert person_id == 0
        def detect(img):
            seen.append(img.name)
            return ["0 0.500000 0.500000 0.400000 0.900000"]
        return detect

    monkeypatch.setattr(remap_public, "make_person_detector", fake_factory)
    run(monkeypatch, src, out, "--add-person")
    text = (out / "train" / "labels" / "kitchenhygiene__train__worker.txt").read_text()
    assert text.splitlines()[-1].startswith("0 ")
    assert seen == ["worker.jpg"]  # only images we keep get the detector
    err = capsys.readouterr().err
    assert "never labels ['mask', 'no_mask']" in err


def test_new_aliases():
    names, name_to_id, aliases = remap_public.load_classes()
    for src, ours in {"gloved": "gloves", "not-gloved": "no_gloves", "with_mask": "mask",
                      "without_mask": "no_mask", "mask_weared_incorrect": "no_mask"}.items():
        assert aliases[src] == ours
