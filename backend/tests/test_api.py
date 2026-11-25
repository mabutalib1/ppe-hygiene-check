import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DETECTOR", "fake")
    monkeypatch.setenv("CAMERA_SOURCE", "synthetic")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_health_and_ws_and_events(client):
    deadline = time.time() + 5
    while time.time() < deadline:
        h = client.get("/health").json()
        if h["ok"] and h["fps"] > 0:
            break
        time.sleep(0.2)
    assert h["ok"] and h["model"]["loaded"]

    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "status"

    assert client.get("/events?limit=5").json() == []
    assert client.get("/snapshots/evt_0001.jpg").status_code == 404
    assert client.get("/snapshots/..%2Fevents.db.jpg").status_code in (400, 404)


def test_store_roundtrip(tmp_path):
    from app.store import EventStore
    s = EventStore(tmp_path / "e.db", tmp_path / "snaps")
    assert s.next_event_number() == 1
    s.add({"event_id": "evt_0001", "person_id": 3, "item": "gloves", "change": "removed",
           "camera": "kitchen-1", "time": "2026-12-10T14:32:10+03:00"}, "evt_0001.jpg")
    s.resolve("evt_0001", "2026-12-10T14:32:40+03:00", 30.0)
    (row,) = s.recent()
    assert row["duration_s"] == 30.0 and row["snapshot_url"] == "/snapshots/evt_0001.jpg"
    assert s.next_event_number() == 2


def test_dashboard_endpoints(client):
    st = client.get("/stats?days=7").json()
    assert st["total"] == 0 and len(st["by_hour"]) == 24
    assert set(st["session"]["compliance"]) == {"mask", "gloves"}

    cfg = client.get("/config").json()
    assert cfg["model"]["detector"] == "fake" and cfg["engine"]["window_s"] > 0

    assert isinstance(client.get("/training/results").json()["runs"], list)
    assert "runs" in client.get("/evaluation/results").json()
    assert "clips" in client.get("/dataset/summary").json()
    assert client.get("/events?item=shoes").status_code == 400
    assert client.get("/events?status=open&item=gloves&days=1").json() == []


def test_store_filters_and_stats(tmp_path):
    from app.store import EventStore
    s = EventStore(tmp_path / "e.db", tmp_path / "snaps")
    s.add({"event_id": "evt_0001", "person_id": 1, "item": "gloves", "change": "removed",
           "camera": "k", "time": "2026-12-10T14:00:00+03:00"}, None)
    s.add({"event_id": "evt_0002", "person_id": 2, "item": "mask", "change": "missing",
           "camera": "k", "time": "2026-12-10T15:30:00+03:00"}, None)
    s.resolve("evt_0001", "2026-12-10T14:00:20+03:00", 20.0)

    assert [r["event_id"] for r in s.query(status="open")] == ["evt_0002"]
    assert [r["event_id"] for r in s.query(item="gloves")] == ["evt_0001"]
    assert s.query(since="2026-12-11") == []

    st = s.stats("2026-12-01")
    assert st["total"] == 2 and st["open"] == 1 and st["mean_fix_s"] == 20.0
    assert st["by_item"] == {"gloves": 1, "mask": 1}
    assert st["by_hour"][14]["count"] == 1 and st["by_hour"][15]["count"] == 1
    assert st["by_day"] == [{"day": "2026-12-10", "gloves": 1, "mask": 1}]


def test_result_readers(tmp_path):
    from app.results import dataset_summary, evaluation_results, redact_source, training_results
    assert training_results(tmp_path / "none.json") == {"runs": []}
    assert evaluation_results(tmp_path / "none.json")["runs"] == []
    log = tmp_path / "log.csv"
    log.write_text("file,split,angle,clip_type,people,lighting,notes\n"
                   "a.mp4,train,A,fully_compliant,2,lights_on,\n"
                   "e1.mp4,event,A,violation_event,2,lights_on,x\n")
    d = dataset_summary(log)
    assert d["clips"] == 2 and d["by_split"] == {"train": 1, "event": 1}
    assert redact_source("rtsp://admin:pw@10.0.0.5/s1") == "rtsp://***@10.0.0.5/s1"
    assert redact_source("0") == "0"


def test_processor_does_not_break_open_events(tmp_path):
    """Regression: the processor used to pop "t" from the engine's open_event, so the
    later "resolved" step crashed with KeyError('t')."""
    import numpy as np
    from app.engine import ViolationEngine
    from app.processor import Processor
    from app.store import EventStore
    from app.types import Detection

    class Cam:
        def read(self):
            return None, 0.0

    store = EventStore(tmp_path / "e.db", tmp_path / "s")
    proc = Processor(Cam(), lambda f: [], ViolationEngine(), store)
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    person = Detection("person", 0.9, (100, 100, 600, 1000), 1)

    def hand(lbl):
        return [person, Detection(lbl, 0.9, (120, 500, 200, 580))]

    got = []
    proc.on_message = got.append
    t = 1_800_000_000.0  # a real timestamp: Windows can't localise times near 1970
    for lbl, secs in (("gloves", 5), ("no_gloves", 5), ("gloves", 5)):
        proc.detector = lambda f, lbl=lbl: hand(lbl)
        for _ in range(int(secs * 10)):
            proc._step(frame, t)
            t += 0.1
    kinds = [m["type"] for m in got if m.get("type") != "status"]
    assert kinds == ["violation", "resolved"]
    (row,) = store.recent()
    assert row["ended_at"] is not None and row["duration_s"] > 0
