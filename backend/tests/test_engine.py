from app.config import EngineConfig
from app.engine import ViolationEngine, assign_items, observe, raw_config
from app.types import Detection, Obs

FPS = 10
P1 = (100, 100, 300, 700)
P2 = (900, 100, 1100, 700)


def person(tid, box=P1):
    return Detection("person", 0.9, box, tid)


def item(label, box_in=P1, conf=0.8):
    x1, y1, x2, y2 = box_in
    return Detection(label, conf, (x1 + 20, y1 + 20, x1 + 60, y1 + 60))


def run(engine, seconds, frame_fn, t0=0.0):
    """Feed `seconds` of frames at FPS; collect events."""
    events = []
    n = int(seconds * FPS)
    for i in range(n):
        t = t0 + i / FPS
        _, ev = engine.update(t, frame_fn(t))
        events += ev
    return events, t0 + n / FPS


def compliant(tid=1, box=P1):
    return lambda t: [person(tid, box), item("mask", box), item("hairnet", box),
                      item("gloves", box)]


def no_gloves(tid=1, box=P1):
    return lambda t: [person(tid, box), item("mask", box), item("hairnet", box),
                      item("no_gloves", box)]


def kinds(events):
    return [(e["type"], e["item"], e.get("change")) for e in events]


# ------------------------------------------------------------------ basics
def test_assign_picks_largest_overlap_and_drops_strays():
    people = [person(1, P1), person(2, P2)]
    stray = Detection("mask", 0.9, (500, 50, 540, 90))
    out = assign_items(people, [item("mask", P2), stray], 0.5)
    assert [d.label for d in out[2]] == ["mask"] and out[1] == []


def test_gloves_any_bare_hand_is_not_wearing():
    assert observe("gloves", [item("gloves"), item("no_gloves")]) == Obs.NOT_WEARING
    assert observe("gloves", []) == Obs.NOT_VISIBLE


def test_compliant_person_raises_nothing():
    eng = ViolationEngine(EngineConfig())
    events, _ = run(eng, 20, compliant())
    assert events == []
    status, _ = eng.update(20.0, compliant()(20.0))
    assert status[0]["items"] == {"mask": "ok", "hairnet": "ok", "gloves": "ok"}


def test_removal_is_one_event_then_resolved_with_duration():
    eng = ViolationEngine(EngineConfig())
    ev1, t = run(eng, 10, compliant())
    ev2, t = run(eng, 10, no_gloves(), t)
    ev3, t = run(eng, 10, compliant(), t)
    assert ev1 == []
    assert kinds(ev2) == [("violation", "gloves", "removed")]
    assert kinds(ev3) == [("resolved", "gloves", "put_back")]
    assert 9 <= ev3[0]["duration_s"] <= 13
    # alert delay: removal at t=10, alert within a few seconds
    assert 10 < ev2[0]["t"] <= 13


def test_single_frame_flicker_does_not_alert():
    eng = ViolationEngine(EngineConfig())
    flicker = lambda t: no_gloves()(t) if int(t * FPS) % 10 == 0 else compliant()(t)
    events, _ = run(eng, 30, flicker)
    assert events == []


def test_raw_mode_alerts_on_flicker():
    eng = ViolationEngine(raw_config())
    flicker = lambda t: no_gloves()(t) if int(t * FPS) % 10 == 0 else compliant()(t)
    events, _ = run(eng, 30, flicker)
    assert sum(e["type"] == "violation" for e in events) >= 25


def test_entering_without_item_is_missing():
    eng = ViolationEngine(EngineConfig())
    events, _ = run(eng, 6, no_gloves())
    assert kinds(events) == [("violation", "gloves", "missing")]


def test_hidden_item_is_unknown_never_alerts():
    eng = ViolationEngine(EngineConfig())
    hidden = lambda t: [person(1), item("mask"), item("hairnet")]  # hands hidden
    events, t = run(eng, 10, hidden)
    status, _ = eng.update(t, hidden(t))
    assert events == [] and status[0]["items"]["gloves"] == "unknown"


def test_cooldown_limits_repeat_alerts():
    eng = ViolationEngine(EngineConfig(cooldown_s=30))
    events, t = run(eng, 5, compliant())
    for _ in range(3):  # remove / put back three times within 30 s
        e1, t = run(eng, 5, no_gloves(), t)
        e2, t = run(eng, 5, compliant(), t)
        events += e1 + e2
    assert sum(e["type"] == "violation" for e in events) == 1


def test_low_confidence_items_ignored():
    eng = ViolationEngine(EngineConfig(item_conf=0.4))
    weak = lambda t: [person(1), item("no_mask", conf=0.2), item("hairnet"),
                      item("gloves")]
    events, _ = run(eng, 10, weak)
    assert events == []


def test_two_people_tracked_independently():
    eng = ViolationEngine(EngineConfig())
    both = lambda t: compliant(1, P1)(t) + (no_gloves(2, P2)(t) if t >= 10 else compliant(2, P2)(t))
    events, _ = run(eng, 20, both)
    assert [(e["person_id"], e["item"], e["change"]) for e in events] == [(2, "gloves", "removed")]


def test_id_switch_does_not_refire_missing_alert():
    """Same person, no hairnet, hidden for 2 s, comes back with a new track ID."""
    eng = ViolationEngine(EngineConfig())
    no_net = lambda tid: (lambda t: [person(tid), item("mask"), item("no_hairnet"),
                                     item("gloves")])
    e1, t = run(eng, 8, no_net(1))
    e2, t = run(eng, 2, lambda t: [], t)          # hidden behind someone
    e3, t = run(eng, 8, no_net(7), t)             # tracker gave a new ID
    assert kinds(e1) == [("violation", "hairnet", "missing")]
    assert e2 == [] and e3 == []
    status, _ = eng.update(t, no_net(7)(t))
    assert status[0]["id"] == 1                   # display ID kept


def test_new_person_far_away_gets_new_id():
    eng = ViolationEngine(EngineConfig())
    run(eng, 5, compliant(1, P1))
    _, t = run(eng, 2, lambda t: [], 5)
    status, _ = eng.update(t, compliant(9, P2)(t))
    assert status[0]["id"] == 2
