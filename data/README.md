# Data

Nothing in this folder is committed except this file (see `.gitignore`).

```
data/
  raw/<dataset-name>/   downloaded Roboflow exports (YOLO format)
  merged/               unified dataset produced by scripts/merge_datasets.py
  local/                our own photos from partner cafés/restaurants
```

`local/` should hold the **validation set from real Saudi venues**. Report accuracy on this set, not on the public data.
