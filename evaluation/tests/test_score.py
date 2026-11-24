import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "score_events", Path(__file__).resolve().parents[1] / "score_events.py")
se = importlib.util.module_from_spec(spec)
spec.loader.exec_module(se)

GT = [
    {"clip": "e01", "person": "left", "item": "gloves", "change": "removed", "time_sec": "42"},
    {"clip": "e01", "person": "left", "item": "gloves", "change": "put_back", "time_sec": "71"},
    {"clip": "e02", "person": "right", "item": "mask", "change": "removed", "time_sec": "18"},
]


def p(clip, item, change, t):
    return {"clip": clip, "person": "3", "item": item, "change": change, "time_sec": str(t)}


def test_perfect_run():
    s = se.score(GT, [p("e01", "gloves", "removed", 45), p("e02", "mask", "removed", 20)], 5.0)
    assert s["caught"] == 2 and s["false_alarms"] == 0 and s["mean_delay_s"] == 2.5


def test_late_or_wrong_item_is_miss_and_false_alarm():
    s = se.score(GT, [p("e01", "gloves", "removed", 60), p("e02", "hairnet", "removed", 19)], 5.0)
    assert s["caught"] == 0 and s["false_alarms"] == 2 and s["false_per_5min"] == 2.0


def test_duplicate_alerts_count_once():
    preds = [p("e01", "gloves", "removed", 43), p("e01", "gloves", "removed", 44)]
    s = se.score(GT, preds, 10.0)
    assert s["caught"] == 1 and s["false_alarms"] == 1


def test_put_back_rows_ignored():
    s = se.score(GT, [p("e01", "gloves", "put_back", 72)], 5.0)
    assert s["alerts"] == 0 and s["gt_events"] == 2
