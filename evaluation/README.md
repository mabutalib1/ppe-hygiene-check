# Evaluation

Two levels:

1. **Model (single frames):** `model.val(split="test")` on the held-out test videos. `training/train.py` runs it and logs per-class mAP50 to `training/results.md` and `training/results.json` (the dashboard's Model page). Also check precision, recall and the confusion matrix in the run folder.
2. **System (events):** does the whole pipeline catch real violations on the event clips?

## Level 2 steps

1. Put the event clips (never uploaded to Roboflow) in `data/event_clips/` (not in git).
2. For each clip, write down what really happened in `ground_truth/events.csv`:

   ```
   clip,person,item,change,time_sec
   e01,left,gloves,removed,42
   e01,left,gloves,put_back,71
   ```
   `clip` is the file name without extension. `change` is `removed`, `missing` (entered without) or `put_back`.

3. Run the pipeline twice, once with time logic and once raw:

   ```bash
   python evaluation/run_events.py --clips data/event_clips --weights backend/weights/best.pt --out evaluation/out/timelogic.csv
   python evaluation/run_events.py --clips data/event_clips --weights backend/weights/best.pt --out evaluation/out/raw.csv --raw
   ```

4. Score both:

   ```bash
   python evaluation/score_events.py evaluation/ground_truth/events.csv evaluation/out/durations.csv \
       evaluation/out/timelogic.csv evaluation/out/raw.csv --json evaluation/results.json
   ```

   `--json` saves the scores for the dashboard's Evaluation page. Commit `evaluation/results.json`.

   ```
   run                        caught  false/5min  delay s  alerts
   timelogic                9/10   90%        0.60      2.8      10
   raw                     10/10  100%       38.20      0.3     201
   ```
   *(example layout, not real numbers)*. The raw vs time-logic comparison is the slide that shows the tracking layer is worth it.

| Metric | Goal |
|---|---|
| Events caught | ≥ 80% |
| False alarms | < 1 per 5 minutes |
| Alert delay | < 5 s |
| Live speed | ≥ 10 fps (see `/health` on the demo laptop) |

## Tuning

Change the `CHECK_*` values in `backend/.env` (window, ratios, cooldown) and rerun step 3. Too many false alarms → longer window or stricter ratio. Missed removals → the opposite. Tune on the event clips, then don't touch the settings again before the final numbers.

**Matching note:** ground truth says "left/right" and the system says "Person 3", so matching uses clip + item + time only. Keep one violation per item at a time in each clip.
