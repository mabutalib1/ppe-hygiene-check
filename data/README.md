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

1. Object Detection project, classes spelled exactly as in `training/classes.yaml` (`person` optional, no hairnet)
2. Upload videos one at a time, sampling **0.5 fps**, split chosen to match the file name
3. Labeling jobs per batch, **Review Mode on**, paste `labeling_rules.md`
4. Generate version: **do NOT click Rebalance**. Auto-Orient on, resize 640×640. Augment (train only): brightness/exposure ±20%, slight blur, small noise, horizontal flip. No vertical flip, no big rotations
5. Public data (`training/remap_public.py`) goes into **train only** (see below)

## Public datasets (Roboflow Universe)

Checked 2026-11-25. The tables list what each dataset contains; its hairnet labels are dropped since hairnet is not checked (`docs/decisions.md` #8). Download each as a YOLO export into `data/public/<name>/` (gitignored), remap, then upload the output to Roboflow with split **train**.

| Dataset | Images | Gives us | Licence | Use |
|---|---|---|---|---|
| [KitchenHygiene](https://universe.roboflow.com/kitchen-hygiene-efuu5/kitchenhygiene) | 9.4k | hairnet / no_hairnet, gloves / no_gloves (CCTV video frames) | CC BY 4.0 | **Main one.** Add after model v1 (see below) |
| [Gloves Annotated Dataset](https://universe.roboflow.com/sana-ali/gloves-annotated-dataset) | 1k | gloves / no_gloves (video frames) | Public domain | Yes |
| [Food Industry PPE](https://universe.roboflow.com/proof-87nsb/food-industry-ppe) | 188 | person, mask / no_mask, gloves / no_gloves | CC BY 4.0 | Optional |
| [Face mask, 3-class](https://universe.roboflow.com/group-tbd/real-time-face-mask-detection-and-validation-system-dataset) | 1.7k | mask / no_mask incl. mask under the nose (close-up faces) | check page | Optional, mask only |
| [Hairnet and Mask Detection](https://universe.roboflow.com/tata-meta-19tsj/hairnet-and-mask-detection-1ksyo) (Tata Meta) | 18.4k | mask / no_mask, hairnet / no_hairnet (kitchen CCTV frames + close-ups) | CC BY 4.0 | Yes, main mask source |
| [FinalDataset-Version2](https://universe.roboflow.com/idp-kwqac/finaldataset-version2) (IDP) | 24.1k | all 3 items, worn / absent (top-down ceiling camera, clinical simulation) | CC BY 4.0 | Yes, top-down angle |
| [1](https://universe.roboflow.com/mhm-sjqug/1-yilra) (mhm) | 8.1k | maskon / maskoff, glove, hairnet (kitchen CCTV frames) | Public domain | Yes |

**Duplicates.** mhm reuses KitchenHygiene's source videos, and IDP contains other public sets. `build_public_v0.py` finds near-identical frames across datasets (difference hash, `--dedup-dist 3`), keeps the copy with the richest labels, and puts videos that share a frame in the same split, so no frame leaks between splits.

Skipped: kitchen-ppe (same source as KitchenHygiene, duplicates), chef1 (no `no_mask`; a chef hat is not a hairnet), knowledgeflex Handglove (messy classes).

**Missing labels.** KitchenHygiene never labels `person`, `mask`, `no_mask`; the mask set never labels hairnet or gloves. Unlabeled people and masks teach the model they are background. Person boxes are added automatically with a stock COCO-pretrained YOLO (`--add-person`). The other gaps stay in v0, which is why v0 is a pre-labeling tool, not the final model.

### Model v0: public data only (no labeling)

The list lives in `training/public_datasets.yaml`. One command downloads, remaps, adds person boxes, merges and splits by source video into ~80% train, ~10% valid and ~10% test, with every class and every dataset in each split when the data allows (otherwise it prints which one is missing). It does **not** train:

```bash
export ROBOFLOW_API_KEY=xxxx        # your key, never commit it
python training/build_public_v0.py
```

Output: `data/public/v0/data.yaml` (gitignored). It prints the training command, e.g. on the RTX 5080:

```bash
python training/train.py --data data/public/v0/data.yaml --device 0 --batch 32 --note "v0 public data only"
```

v0's score is on public frames, not our videos, so it's not a result to present. Use v0 for **Label Assist** on our own frames (fewer boxes to draw), then train v1 = public + our labeled images, scored on our own test videos.

**Credit:** CC BY 4.0 needs attribution. Put the dataset names and links on the sources slide.

## Consent

Only film people who agreed. Footage stays inside the team.
