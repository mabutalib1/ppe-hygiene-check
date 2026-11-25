# Decisions and changes to the plan

Changes made while reviewing `implementation_plan.md`. Discuss them in the group, then update the plan.

| # | Issue in the plan | Decision |
|---|---|---|
| 1 | 20–30 clips × 1–3 min at **1 fps** = 1,200–5,400 frames, not 800–1,500 | Sample at **0.5 fps**, or start with ~15 clips. Label more only where the model is weak. |
| 2 | Clear gloves look like bare skin from 2.2–2.5 m | **Blue or black gloves only** for the demo and recordings. Clear gloves are a stated limitation. |
| 3 | Cooldown is per track ID, so an ID switch re-fires "entered without hairnet" | **ID-switch guard** in `backend/app/engine.py`: a new track close to a person lost in the last 10 s inherits that person (same display ID, same cooldown, no new alert). |
| 4 | Nails are on the restaurant's manual checklist but not in the system | Say it in the presentation: nails can't be judged from CCTV height. Nails stay a manual check (possible later: a close-up check-in station). |
| 5 | A camera tilted down sees the top of the head, so the lower face is often hidden | Expect many `unknown` mask states. Record top-down hard cases (looking down at the counter). |
| 6 | The tracker and the violation logic could use different confidence thresholds | `backend/app/bytetrack_check.yaml` sets `track_high_thresh` / `new_track_thresh` to 0.40 = `CHECK_ITEM_CONF`. |
| 7 | Which items does the system check? | **Scope cut to gloves, hairnet, mask** (2026-11-24). `uniform` / `no_uniform` removed: 7 classes instead of 9. Uniform stays a manual check. The plan's staff-vs-customer idea (uniform = staff) no longer has a signal. |
| 8 | Our labeled dataset (Roboflow `ppe-vaqlv` v1) has only `gloves`, `no_gloves`, `mask`, `no_mask`: no `person`, no hairnet | **Hairnet dropped** (2026-11-25): the system checks gloves and mask only; hairnet stays a manual check. **People come from a stock COCO model**: when the weights have no `person` class, `backend/app/detector.py` tracks people with `yolo26n.pt` (`PERSON_WEIGHTS`) and our model only finds the items. Two models per frame, no person labeling needed. |

## Mapping from the manual checklist

| Manual item | In the system |
|---|---|
| Facemask | `mask` / `no_mask` (mask under the nose = `no_mask`) |
| Hairnet | Not automated (see #8) |
| Hair | Not automated (see #8) |
| Gloves | `gloves` / `no_gloves`, one box per hand |
| Uniform | Not automated (see #7) |
| Nails | Not automated (see #4) |
