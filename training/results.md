# Training results

One row per run, appended by `train.py`. Scores are on the **test videos** (split by video). The per-class columns are mAP50.

This table becomes the "how the model improved" slide.

| Date | Dataset | Model | imgsz | mAP50 | mAP50-95 | person | mask | no_mask | gloves | no_gloves | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-25 | v1 | yolo26s | 640 | 0.833 | 0.475 | - | 0.85 | 0.83 | 0.80 | 0.86 | v1 our data only |
