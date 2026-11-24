"""SQLite event store + snapshot folder."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id    TEXT PRIMARY KEY,
    person_id   INTEGER NOT NULL,
    item        TEXT NOT NULL,
    change      TEXT NOT NULL,
    camera      TEXT NOT NULL,
    time        TEXT NOT NULL,
    ended_at    TEXT,
    duration_s  REAL,
    snapshot    TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(time DESC);
"""


class EventStore:
    def __init__(self, db_path: Path, snapshot_dir: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir = snapshot_dir
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)

    def next_event_number(self) -> int:
        with self._lock:
            row = self._db.execute(
                "SELECT MAX(CAST(SUBSTR(event_id, 5) AS INTEGER)) FROM events").fetchone()
        return (row[0] or 0) + 1

    def add(self, ev: dict, snapshot: Optional[str]) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO events (event_id, person_id, item, change, camera, time, snapshot)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ev["event_id"], ev["person_id"], ev["item"], ev["change"], ev["camera"],
                 ev["time"], snapshot))

    def resolve(self, event_id: str, ended_at: str, duration_s: float) -> None:
        with self._lock, self._db:
            self._db.execute("UPDATE events SET ended_at = ?, duration_s = ? WHERE event_id = ?",
                             (ended_at, duration_s, event_id))

    def recent(self, limit: int = 50) -> List[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM events ORDER BY time DESC, event_id DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["snapshot_url"] = f"/snapshots/{d['event_id']}.jpg" if d.pop("snapshot") else None
            out.append(d)
        return out

    def snapshot_path(self, event_id: str) -> Path:
        return self.snapshot_dir / f"{event_id}.jpg"
