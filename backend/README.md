# Backend

FastAPI server that reads the camera, runs detection + tracking + violation logic, and serves results to the app. The app never runs the model.

```
camera → LatestFrameReader → YOLO + ByteTrack → ViolationEngine → MJPEG / WebSocket / SQLite
```

| File | Role |
|---|---|
| `app/camera.py` | Background reader, always returns the newest frame (RTSP, webcam, file, synthetic, Nebras live) |
| `app/nebras.py` | Shop's live camera through the Nebras camera API: sign-in, live session, lease renew/release |
| `app/detector.py` | `YoloDetector` (model.track + ByteTrack) and `FakeDetector` (scripted demo). Weights without a `person` class → people are tracked by a stock COCO model (`PERSON_WEIGHTS`, default `yolo26n.pt`, downloaded on first run) and ours only finds items |
| `app/engine.py` | Item→person assignment, 3 s window vote, events, cooldown, ID-switch guard |
| `app/processor.py` | The processing loop |
| `app/draw.py` | Boxes: green OK, red violation, grey unknown |
| `app/store.py` | SQLite events + snapshots, filters and aggregates for the dashboard |
| `app/results.py` | Reads training / evaluation / recording-log files for the dashboard |
| `app/main.py` | Endpoints |
| `app/bytetrack_check.yaml` | Tracker thresholds aligned with `CHECK_ITEM_CONF` |

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # edit CAMERA_SOURCE etc.

# no model yet? run with scripted detections + synthetic camera
DETECTOR=fake CAMERA_SOURCE=synthetic uvicorn app.main:app --host 0.0.0.0 --port 8000

# real model + phone IP-camera app
DETECTOR=yolo WEIGHTS=weights/best.pt CAMERA_SOURCE=http://192.168.1.20:8080/video \
  uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://<laptop-ip>:8000/dashboard/` for the web dashboard (build it once: see [`../dashboard/README.md`](../dashboard/README.md)), or `/stream` for the bare annotated video.

### The shop's live camera (Nebras)

`CAMERA_SOURCE=nebras` reads the shop camera through the Nebras camera API instead of a local camera, so it also works on a cloud server (the online demo on Render).

```bash
# in .env: NEBRAS_BRAND_ID, NEBRAS_EMAIL, NEBRAS_PASSWORD (admin account with camera access)
python -m app.nebras cameras                     # pick a dahua channel with play=yes
CAMERA_SOURCE=nebras NEBRAS_CHANNEL_ID=<channel id> uvicorn app.main:app --port 8000
```

How it works: sign in (`POST /auth/login`), check the channel in the brand's camera list (`online`, `canPlay`), start a live session (`POST /camera-cloud/channels/:id/live`), read the HLS stream with OpenCV, renew the lease every 10 minutes and release it on exit. Every reconnect starts a new session; leases and URLs are never reused. `/health` shows `camera.live` (which camera) and `camera.error` (why it is not connected).

- Only **Dahua (HLS)** cameras work. Hikvision returns its own browser-SDK protocol and is refused with a clear error.
- The email/password, JWT and stream URL are secrets: env vars only, never in git or logs.
- Expect a few seconds of delay: HLS is segmented video, not a direct camera feed.

### Docker

Build from the **repo root**: the image also builds the dashboard and copies the result files it shows.

```bash
docker build -f backend/Dockerfile -t check .
docker run --env-file backend/.env -p 8000:8000 check     # → http://localhost:8000
```

A webcam inside Docker needs `--device /dev/video0` (Linux only). For the demo, prefer running natively or use an RTSP/HTTP camera source.

## Endpoints

| Endpoint | Returns |
|---|---|
| `GET /health` | Server, camera and model status, fps |
| `GET /stream` | Annotated live video (MJPEG) |
| `WS /ws` | `status` messages ~2×/s, plus `violation` and `resolved` events instantly |
| `GET /events?limit=50` | Event history, newest first. Optional `item=gloves`, `status=open\|resolved`, `days=7` |
| `GET /snapshots/{event_id}.jpg` | Saved frame for one event |
| `GET /stats?days=7` | Counts by item / hour / day, open now, time to fix, time in compliance since start |
| `GET /config` | Camera, model and `CHECK_*` settings (camera passwords hidden) |
| `GET /training/results` | `training/results.json` (empty list until the first run) |
| `GET /evaluation/results` | `evaluation/results.json` (empty until scored) |
| `GET /dataset/summary` | Clip counts from `data/recording_log.csv` |
| `GET /dashboard/` | The web dashboard, when `dashboard/dist` is built |

Messages:

```json
{"type": "status", "fps": 9.8, "people": [{"id": 3, "items": {"mask": "ok", "gloves": "violation"}}]}
{"type": "violation", "event_id": "evt_0042", "person_id": 3, "item": "gloves", "change": "removed", "camera": "kitchen-1", "time": "2026-12-10T14:32:10+03:00", "snapshot_url": "/snapshots/evt_0042.jpg"}
{"type": "resolved", "event_id": "evt_0042", "person_id": 3, "item": "gloves", "change": "put_back", "time": "2026-12-10T14:32:40+03:00", "duration_s": 30.0}
```

`change` is `removed` (was OK, now violation), `missing` (first decision is a violation, e.g. entered without a mask) or `put_back`.

## Violation logic

All values come from `.env` (`CHECK_*`); defaults are the plan's starting guesses.

- An item box belongs to the person box that contains most of it (≥ 50%).
- Each frame records *wearing / not wearing / not visible* per person per item.
- Over the last 3 s: **violation** if ≥ 70% of visible frames say not wearing; **OK** if most say wearing; **unknown** if the item was visible in < 40% of frames. Unknown never alerts.
- A new person needs 3 s of history before any decision.
- One alert per person per item per 30 s.
- **ID-switch guard:** a new track appearing close to a recently lost one (within 10 s) inherits that person, so an ID switch doesn't re-fire "entered without a mask".

## Tests

```bash
pytest
```
