# Data plan

## Public data (Phase 1)

| Item | Coverage | Source |
|---|---|---|
| Facemask | Good | kitchen-hygiene-gear, kitchen-attire-detect-2, kitchen-hairnet-mask |
| Hairnet | Good (small sets, so merge several) | same + hairnet-detection |
| Gloves | Good (~11k images) | gloves-and-bare-hand-dataset |
| Hair exposed | Indirect only (`no_hairnet`) | needs relabeling |
| Nails | Segmentation only, no pass/fail labels | nails_segmentation (Roboflow) |
| Uniform | None | custom |

Sources and versions live in `configs/datasets.yaml`.

## Custom data to collect

1. **Restaurant's past inspection photos.** Ask for these first. They're already split by item (nails / hair / mask / hairnet / gloves / uniform) and may carry pass/fail.
2. **Uniform:** 50–100 photos per venue, both correct and incorrect.
3. **Nails:** close-ups of hands, labeled `ok` / `long` / `polish` / `dirty`, a few hundred per class.
4. **Hair:** head crops labeled `covered` / `exposed`.
5. **Local validation set:** 200–500 images from real venues (lighting, uniforms, skin tones).

## Rules

- Get written consent from staff before taking photos.
- Never commit images to git.
- Label in Roboflow or CVAT and export in YOLO format.
- Watch for transparent gloves, which look like bare skin. Record which glove types each venue uses.
