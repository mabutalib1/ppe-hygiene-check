# Dashboard

Web dashboard for the supervisor's office or a wall screen, and the screen to show in the presentation. English and Arabic (RTL), light theme. The phone app stays the on-the-move tool that buzzes.

React + Vite + Recharts. The backend serves the built dashboard at **`http://<laptop-ip>:8000/dashboard/`**, so the demo still needs only one server.

| Page | Shows | Data from |
|---|---|---|
| **Live** | Camera stream, a card per person (mask / hairnet / gloves), live alert feed, pop-ups + sound | `WS /ws`, `/stream`, `/stats?days=1` |
| **Alerts** | Full history with snapshots, filters (period, item, open/resolved), CSV export | `/events` |
| **Insights** | Alerts per day and per hour, by item, time to fix, time in compliance | `/stats` |
| **Model** | Running detector, the 7 classes, recorded clips, training runs (mAP per class, progress, table) | `/config`, `/dataset/summary`, `/training/results` |
| **Evaluation** | The 4 goals (caught, false alarms, delay, fps), time logic vs raw | `/evaluation/results`, live fps |
| **System** | Server / camera / model / speed health, all `CHECK_*` violation settings | `/health`, `/config` |

## Run

```bash
# 1. backend (demo mode, no model needed)
cd backend
DETECTOR=fake CAMERA_SOURCE=synthetic uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2a. use it: build once, the backend serves it
cd dashboard
npm install
npm run build              # → open http://localhost:8000/dashboard/

# 2b. or work on it with hot reload (calls go to the backend on :8000)
npm run dev                # → http://localhost:5173/dashboard/
```

Backend somewhere else? `CHECK_BACKEND=http://192.168.1.20:8000 npm run dev`, or build with `VITE_API_URL=http://192.168.1.20:8000 npm run build`.

## Pages that fill themselves in later

Nothing here is fake: until a step is done, its page shows an empty state that says what to run.

| Page | Fills in when | File it reads |
|---|---|---|
| Model → training runs | `training/train.py` finishes a run | `training/results.json` (commit it) |
| Model → recorded data | you log clips | `data/recording_log.csv` |
| Evaluation | `score_events.py ... --json evaluation/results.json` | `evaluation/results.json` (commit it) |

In demo mode (`DETECTOR=fake`) the top bar shows a **Demo mode** badge so nobody mistakes scripted detections for the model.

## Brand

The شيّك logo (from `shayyek-logo-animated.html`) lives in `src/brand/Logo.jsx` + `logo.css`, with the same markup and CSS as the original. Its corners lock on and the check pops in once when the dashboard opens. The looping scan line exists (`<Logo live />`) but is off by default so it doesn't pull attention from alerts. The live camera view reuses the logo's viewfinder corners.

Colors come from the logo: accent `#0E9F5E`, ink `#0D2B22`, off-white `#F4F8F5` (set as `--brand*`, `--text`, `--bg` in `src/theme.css`). Page titles use the logo's font, Alexandria. Red (violation) and grey (not visible) keep their meaning. Gloves is amber in charts so it doesn't blend with the brand green.

## Files

| Path | Role |
|---|---|
| `src/theme.css` | All colors, fonts, radii. Brand tokens at the top |
| `src/styles.css` | Layout and components (logical CSS properties, so Arabic mirrors) |
| `src/brand/` | The شيّك logo and the item icons |
| `src/lib/i18n.jsx` | English + Arabic strings and number/date formatting. Add every key to both |
| `src/lib/live.jsx` | The one WebSocket: people, fps, alert feed, toasts, sound |
| `src/lib/api.js` | Fetch helpers, `usePoll`, item and class lists |
| `src/pages/` | One file per page |
