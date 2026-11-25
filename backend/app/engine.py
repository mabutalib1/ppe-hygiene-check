"""Tracking + time logic: turns per-frame detections into per-person states and events.

Pure Python (no model, no OpenCV) so it is fully unit-testable and reusable
by the evaluation scripts.

Per frame:
  1. attach each item box to the person box that contains most of it
  2. record wearing / not_wearing / not_visible per person per item
  3. decide each item's state from the last `window_s` seconds
  4. emit an event when a state changes (OK→VIOLATION = "removed",
     first decision VIOLATION = "missing", VIOLATION→OK = "resolved")

Extra guard (not in the original plan): when a track is lost and a new track
appears close by soon after, the new track inherits the old person record.
That stops ID switches from re-firing "entered without a mask" for the same
person, because the cooldown would otherwise reset with the new ID.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

from .config import EngineConfig
from .types import ITEMS, LABEL_TO_ITEM, Detection, ItemState, Obs, intersection


# ---------------------------------------------------------------- assignment
def assign_items(people: List[Detection], items: List[Detection],
                 min_overlap: float) -> Dict[int, List[Detection]]:
    """track_id -> item detections. Items that fit no person are dropped."""
    out: Dict[int, List[Detection]] = {p.track_id: [] for p in people}
    for it in items:
        if it.area <= 0:
            continue
        best, best_ov = None, 0.0
        for p in people:
            ov = intersection(it.box, p.box) / it.area
            if ov > best_ov:
                best, best_ov = p, ov
        if best is not None and best_ov >= min_overlap:
            out[best.track_id].append(it)
    return out


def observe(item: str, dets: List[Detection]) -> Obs:
    """One frame's observation for one item on one person."""
    wear_lbl, not_lbl = ITEMS[item]
    rel = [d for d in dets if d.label in (wear_lbl, not_lbl)]
    if not rel:
        return Obs.NOT_VISIBLE
    if item == "gloves":
        # two hands: any confident bare hand is a violation
        if any(d.label == not_lbl for d in rel):
            return Obs.NOT_WEARING
        return Obs.WEARING
    best = max(rel, key=lambda d: d.conf)
    return Obs.WEARING if best.label == wear_lbl else Obs.NOT_WEARING


# ---------------------------------------------------------------- per item
@dataclass
class ItemTrack:
    history: Deque[Tuple[float, Obs]] = field(default_factory=deque)
    state: ItemState = ItemState.UNKNOWN
    last_known: Optional[ItemState] = None   # last OK/VIOLATION, ignoring UNKNOWN
    open_event: Optional[dict] = None
    last_alert_t: float = -math.inf

    def push(self, t: float, obs: Obs, window_s: float) -> None:
        self.history.append((t, obs))
        while self.history and self.history[0][0] < t - window_s:
            self.history.popleft()

    def decide(self, cfg: EngineConfig) -> ItemState:
        total = len(self.history)
        visible = [o for _, o in self.history if o != Obs.NOT_VISIBLE]
        if total == 0 or len(visible) / total < cfg.min_visibility:
            return ItemState.UNKNOWN
        bad = sum(o == Obs.NOT_WEARING for o in visible) / len(visible)
        good = 1.0 - bad
        if bad >= cfg.violation_ratio:
            return ItemState.VIOLATION
        if good >= cfg.ok_ratio and bad < cfg.violation_ratio:
            # hysteresis: an open violation needs a clear majority to close
            if self.last_known == ItemState.VIOLATION and good < cfg.violation_ratio:
                return ItemState.VIOLATION
            return ItemState.OK
        return self.last_known or ItemState.UNKNOWN


@dataclass
class Person:
    pid: int                      # display ID (stable across re-entry)
    first_seen: float
    last_seen: float
    center: Tuple[float, float]
    items: Dict[str, ItemTrack] = field(default_factory=lambda: {i: ItemTrack() for i in ITEMS})

    def status(self) -> dict:
        return {"id": self.pid, "items": {k: v.state.value for k, v in self.items.items()}}


# ---------------------------------------------------------------- engine
class ViolationEngine:
    def __init__(self, cfg: EngineConfig | None = None, camera: str = "kitchen-1",
                 event_id_start: int = 1):
        self.cfg = cfg or EngineConfig()
        self.camera = camera
        self.people: Dict[int, Person] = {}          # track_id -> Person
        self.lost: List[Tuple[float, Person]] = []   # (lost_at, Person)
        self._next_pid = 1
        self._next_event = event_id_start

    # -- helpers
    def _new_event_id(self) -> str:
        eid = f"evt_{self._next_event:04d}"
        self._next_event += 1
        return eid

    def _match_lost(self, det: Detection, t: float, diag: float) -> Optional[Person]:
        best, best_d = None, math.inf
        for lost_at, p in self.lost:
            if t - lost_at > self.cfg.reentry_s:
                continue
            d = math.dist(det.center, p.center) / diag
            if d <= self.cfg.reentry_dist and d < best_d:
                best, best_d = p, d
        if best is not None:
            self.lost = [(la, p) for la, p in self.lost if p is not best]
        return best

    # -- main step
    def update(self, t: float, detections: List[Detection],
               frame_size: Tuple[int, int] = (1920, 1080)) -> Tuple[List[dict], List[dict]]:
        """Process one frame. Returns (status list, new events)."""
        cfg = self.cfg
        diag = math.hypot(*frame_size)
        people = [d for d in detections if d.label == "person" and d.track_id is not None]
        items = [d for d in detections
                 if d.label in LABEL_TO_ITEM and d.conf >= cfg.item_conf]

        # register / refresh people
        for det in people:
            p = self.people.get(det.track_id)
            if p is None:
                p = self._match_lost(det, t, diag) or Person(self._alloc_pid(), t, t, det.center)
                self.people[det.track_id] = p
            p.last_seen, p.center = t, det.center

        assigned = assign_items(people, items, cfg.assign_min_overlap)
        events: List[dict] = []

        for det in people:
            p = self.people[det.track_id]
            dets = assigned.get(det.track_id, [])
            for item, track in p.items.items():
                track.push(t, observe(item, dets), cfg.window_s)
                if t - p.first_seen < cfg.decide_after_s:
                    continue
                new = track.decide(cfg)
                events.extend(self._transition(t, p, item, track, new))

        self._expire(t)
        status = [p.status() for p in self._active()]
        return status, events

    def track_to_pid(self) -> Dict[int, int]:
        return {tid: p.pid for tid, p in self.people.items()}

    def _alloc_pid(self) -> int:
        pid = self._next_pid
        self._next_pid += 1
        return pid

    def _transition(self, t: float, p: Person, item: str, tr: ItemTrack,
                    new: ItemState) -> List[dict]:
        events = []
        prev_known = tr.last_known
        tr.state = new
        if new == ItemState.UNKNOWN:
            return events

        if new == ItemState.VIOLATION and prev_known != ItemState.VIOLATION:
            change = "removed" if prev_known == ItemState.OK else "missing"
            if t - tr.last_alert_t >= self.cfg.cooldown_s:
                ev = {
                    "type": "violation",
                    "event_id": self._new_event_id(),
                    "person_id": p.pid,
                    "item": item,
                    "change": change,
                    "camera": self.camera,
                    "t": t,
                }
                tr.open_event, tr.last_alert_t = ev, t
                events.append(ev)
        elif new == ItemState.OK and prev_known == ItemState.VIOLATION and tr.open_event:
            ev = tr.open_event
            events.append({
                "type": "resolved",
                "event_id": ev["event_id"],
                "person_id": p.pid,
                "item": item,
                "change": "put_back",
                "camera": self.camera,
                "t": t,
                "duration_s": round(t - ev["t"], 1),
            })
            tr.open_event = None

        tr.last_known = new
        return events

    def _active(self) -> List[Person]:
        seen, out = set(), []
        for p in self.people.values():
            if id(p) not in seen:
                seen.add(id(p))
                out.append(p)
        return sorted(out, key=lambda p: p.pid)

    def _expire(self, t: float) -> None:
        for tid in [tid for tid, p in self.people.items() if t - p.last_seen > self.cfg.lost_after_s]:
            p = self.people.pop(tid)
            if all(q is not p for q in self.people.values()):
                self.lost.append((t, p))
        self.lost = [(la, p) for la, p in self.lost if t - la <= self.cfg.reentry_s]


def raw_config() -> EngineConfig:
    """Per-frame alerts with no time logic: the baseline for the comparison slide."""
    return EngineConfig(window_s=1e-6, decide_after_s=0.0, min_visibility=0.0,
                        violation_ratio=0.5, ok_ratio=0.5, cooldown_s=0.0,
                        reentry_s=0.0)
