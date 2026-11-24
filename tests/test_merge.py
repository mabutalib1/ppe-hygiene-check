import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("merge", ROOT / "scripts" / "merge_datasets.py")
merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge)


def test_remap_unifies_and_drops():
    classes, name_to_id, aliases = merge.load_unified(ROOT / "configs" / "classes.yaml")
    src = ["with_hairnet", "without_hairnet", "Cockroach", "No_Gloves"]
    remap, dropped = merge.build_remap(src, aliases, name_to_id)
    assert classes[remap[0]] == "hairnet"
    assert classes[remap[1]] == "no_hairnet"
    assert remap[2] is None and dropped == ["Cockroach"]
    assert classes[remap[3]] == "bare_hand"

    text = "0 0.5 0.5 0.1 0.1\n2 0.3 0.3 0.1 0.1\n"
    out = merge.remap_label_text(text, remap)
    assert out == f"{name_to_id['hairnet']} 0.5 0.5 0.1 0.1\n"
