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
