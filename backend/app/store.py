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
        return [self._row(r) for r in rows]

    def query(self, limit: int = 50, item: Optional[str] = None, since: Optional[str] = None,
              status: Optional[str] = None) -> List[dict]:
        """Filtered history, newest first. status: "open" or "resolved"."""
        where, args = [], []
        if item:
            where.append("item = ?")
            args.append(item)
        if since:
            where.append("time >= ?")
            args.append(since)
        if status == "open":
            where.append("ended_at IS NULL")
        elif status == "resolved":
            where.append("ended_at IS NOT NULL")
        sql = "SELECT * FROM events"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY time DESC, event_id DESC LIMIT ?"
        with self._lock:
            rows = self._db.execute(sql, (*args, limit)).fetchall()
        return [self._row(r) for r in rows]

    def stats(self, since: str) -> dict:
        """Aggregates for the dashboard's Insights page (events at or after `since`)."""
        with self._lock:
            q = lambda sql: self._db.execute(sql, (since,)).fetchall()  # noqa: E731
            by_item = q("SELECT item, COUNT(*) FROM events WHERE time >= ? GROUP BY item")
            by_change = q("SELECT change, COUNT(*) FROM events WHERE time >= ? GROUP BY change")
            by_hour = q("SELECT CAST(SUBSTR(time, 12, 2) AS INTEGER), COUNT(*) FROM events"
                        " WHERE time >= ? GROUP BY 1")
            by_day = q("SELECT SUBSTR(time, 1, 10), item, COUNT(*) FROM events"
                       " WHERE time >= ? GROUP BY 1, 2 ORDER BY 1")
            (total, open_now, mean_fix, max_fix), = q(
                "SELECT COUNT(*), SUM(ended_at IS NULL), AVG(duration_s), MAX(duration_s)"
                " FROM events WHERE time >= ?")
            fix_by_item = q("SELECT item, AVG(duration_s) FROM events"
                            " WHERE time >= ? AND duration_s IS NOT NULL GROUP BY item")
        days: dict = {}
        for day, item, n in by_day:
            days.setdefault(day, {"day": day})[item] = n
        return {
            "total": total,
            "open": open_now or 0,
            "mean_fix_s": round(mean_fix, 1) if mean_fix is not None else None,
            "max_fix_s": round(max_fix, 1) if max_fix is not None else None,
            "by_item": {k: n for k, n in by_item},
            "by_change": {k: n for k, n in by_change},
            "by_hour": [{"hour": h, "count": dict(by_hour).get(h, 0)} for h in range(24)],
            "by_day": list(days.values()),
            "fix_by_item": {k: round(v, 1) for k, v in fix_by_item},
        }

    @staticmethod
    def _row(r) -> dict:
        d = dict(r)
        d["snapshot_url"] = f"/snapshots/{d['event_id']}.jpg" if d.pop("snapshot") else None
        return d

    def snapshot_path(self, event_id: str) -> Path:
        return self.snapshot_dir / f"{event_id}.jpg"
