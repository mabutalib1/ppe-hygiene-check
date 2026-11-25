# Build from the REPO ROOT (the image also builds and serves the web dashboard):
#   docker build -f backend/Dockerfile -t check .
#   docker run --env-file backend/.env -p 8000:8000 check      → http://localhost:8000

# ---- 1. web dashboard ----
FROM node:22-slim AS dashboard
WORKDIR /dash
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY dashboard/ ./
RUN npm run build

# ---- 2. backend ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PROJECT_DIR=/srv/project DASHBOARD_DIR=/srv/dashboard
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY backend/requirements.txt .
# CPU-only torch keeps the image small; remove the index line to use a GPU build
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# weights are not in git: put best.pt in backend/weights before building, or set
# WEIGHTS_URL (and CAMERA_SOURCE_URL for a demo video) to fetch them at startup
COPY backend/weights ./weights
# stock COCO model that tracks people when our weights have no person class
RUN python -c "from ultralytics import YOLO; YOLO('yolo26n.pt')"
COPY --from=dashboard /dash/dist ./dashboard
# result files the dashboard's Model / Evaluation pages read (missing ones → empty states)
COPY training/ ./project/training/
COPY evaluation/ ./project/evaluation/
COPY data/recording_log.csv ./project/data/

EXPOSE 8000
# hosts like Render pass the port in $PORT; locally it defaults to 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
