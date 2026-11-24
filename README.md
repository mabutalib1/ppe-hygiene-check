# PPE Hygiene Check — Cafés & Restaurants

Computer vision system that automates the manual staff hygiene inspection used in cafés and restaurants.

Today an inspector takes **6 photos** per employee and marks pass/fail by hand. This project replaces that with a **check-in station**: the employee stands in front of a camera for a few seconds, shows both hands, and the system fills in the same report automatically, with a photo and a pass/fail result for each item.

| Checklist item | What is checked | Method | Phase |
|---|---|---|---|
| Facemask | Worn, worn correctly (nose covered) | YOLO detector | 1 (MVP) |
| Hairnet | Present on head | YOLO detector | 1 (MVP) |
| Gloves | Both hands gloved | YOLO detector + hand count | 1 (MVP) |
| Hair | Fully covered, no exposed hair | Head-crop classifier | 2 |
| Uniform | Matches approved uniform | Embedding similarity vs reference photos | 2 |
| Nails | Short, clean, no polish | Fingertip-crop classifier (check-in only) | 3 |

## Pipeline

```
Camera frame
  → YOLO detector (person, mask, hairnet, glove, bare_hand, ...)
  → assign detections to each person (box overlap)
  → per-item checks  (+ crop classifiers for hair / uniform / nails)
  → rules engine (which items are required for this site/role)
  → report: PASS / FAIL / NEEDS_REVIEW per item + evidence photo
```

Low-confidence results return `NEEDS_REVIEW` instead of guessing, so a supervisor can confirm them.

## Repo structure

```
configs/        classes, dataset sources, site rules
data/           raw + merged datasets (gitignored, see data/README.md)
scripts/        download, merge, and train
src/ppe_check/  pipeline, rules engine, item checks, report
app/            Streamlit check-in station demo
tests/          unit tests
docs/           checklist → CV mapping, data plan
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Download public datasets (needs a free Roboflow API key)
export ROBOFLOW_API_KEY=xxxx
python scripts/download_datasets.py

# 2. Merge them into one YOLO dataset with unified class names
python scripts/merge_datasets.py

# 3. Train the detector
python scripts/train_detector.py --model yolo11n.pt --epochs 100

# 4. Run the check-in demo
streamlit run app/checkin_app.py

# Tests
pytest
```

## Data

Public datasets cover mask, hairnet, and gloves. Hair, uniform, and nails need custom data. See [`docs/data_plan.md`](docs/data_plan.md).

## Roadmap

- [ ] Phase 1: merge public datasets, train detector (mask / hairnet / gloves)
- [ ] Phase 1: check-in station demo with auto-filled report
- [ ] Collect local validation set (Saudi cafés / restaurants)
- [ ] Phase 2: hair-coverage classifier, uniform matching
- [ ] Phase 3: nails classifier
- [ ] Optional: continuous CCTV monitoring with tracking

## Privacy

Images contain employee faces. Collect with consent, keep retention short, and never commit images to this repo.
