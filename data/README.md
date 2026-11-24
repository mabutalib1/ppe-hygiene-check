# Data

No videos or images go in git. Raw videos live in the team's shared drive and Roboflow. This folder holds the plans, rules and ground truth.

| File | What |
|---|---|
| `labeling_rules.md` | Paste into every Roboflow labeling job |
| `recording_log.csv` | One row per recorded clip: who, what, split |
| `../evaluation/ground_truth/events.csv` | What really happened in each event clip |

## Recording setup

- Phone on a tripod or taped high, **2.2–2.5 m up**, tilted down like CCTV
- **1080p, 30 fps, landscape**, same phone and spot for most clips
- Second angle (other corner) for ~20% of clips
- Set: table as counter, cutting board, bowls, utensils (hands holding things matter)
- Props: hairnets, disposable masks, **blue and black gloves** (no clear gloves, see `docs/decisions.md`)

## What to record (1–3 min each, act naturally)

| Clip type | Used for |
|---|---|
| Fully compliant | Training |
| One item missing (different item per person) | Training |
| Mixed and messy | Training |
| Nothing worn | Training |
| Hard cases: holding objects, facing away, blocked, **looking down at the counter** | Training |
| Violation events: start compliant, remove an item halfway | **Testing only, never uploaded to Roboflow** |

Vary: every teammate plus friends, lights on/off/daylight, 1–3 people in frame, different clothes.

## Splitting by video (decide when recording)

- File names: `v07_train_angleA.mp4`, `v18_valid_angleB.mp4`, `v22_test_angleA.mp4`
- About 70% train, 20% valid, 10% test. If possible, the test clips include a person never seen in training
- Event clips: `e01.mp4`, `e02.mp4`, … kept in `data/event_clips/` locally (gitignored), never in Roboflow

## How much

- Upload at **0.5 frames per second**. At 1 fps, 20–30 clips produce 1,200–5,400 frames, which is too much labeling for the first round
- Target 800–1,500 labeled images, with a few hundred boxes for every `no_` class (gloves will need the most)
- Start small (~300 images), train v1, look at the errors, record more of exactly those cases

## Roboflow checklist

1. Object Detection project, 7 classes spelled exactly as in `training/classes.yaml`
2. Upload videos one at a time, sampling **0.5 fps**, split chosen to match the file name
3. Labeling jobs per batch, **Review Mode on**, paste `labeling_rules.md`
4. Generate version: **do NOT click Rebalance**. Auto-Orient on, resize 640×640. Augment (train only): brightness/exposure ±20%, slight blur, small noise, horizontal flip. No vertical flip, no big rotations
5. Public data (`training/remap_public.py`) goes into **train only**

## Consent

Only film people who agreed. Footage stays inside the team.
