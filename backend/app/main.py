"""FastAPI server.

    uvicorn app.main:app --host 0.0.0.0 --port 8000

Endpoints: GET /health, GET /stream (MJPEG), WS /ws, GET /events, GET /snapshots/{id}.jpg
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from . import __version__
from .camera import LatestFrameReader
from .config import Settings
from .detector import build_detector
from .engine import ViolationEngine
from .processor import Processor
from .store import EventStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("check")
EVENT_ID = re.compile(r"^evt_\d{4,}$")


class Hub:
    """Fans out messages from the processor thread to all WebSocket clients."""

    def __init__(self):
        self.clients: Set[WebSocket] = set()
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.loop: asyncio.AbstractEventLoop | None = None

    def publish_threadsafe(self, msg: dict) -> None:
        if self.loop is None:
            return
        def put():
            if self.queue.full():
                self.queue.get_nowait()  # drop oldest rather than block
            self.queue.put_nowait(msg)
        self.loop.call_soon_threadsafe(put)

    async def run(self) -> None:
        while True:
            msg = await self.queue.get()
            dead = []
            for ws in list(self.clients):
                try:
                    await ws.send_json(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.clients.discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = Settings.from_env()
    store = EventStore(s.db_path, s.snapshot_dir)
    engine = ViolationEngine(s.engine, camera=s.camera_name,
                             event_id_start=store.next_event_number())
    model_error = None
    try:
        detector = build_detector(s)
    except Exception as e:
        log.error("could not load detector: %s", e)
        model_error, detector = repr(e), None

    camera = LatestFrameReader(s.camera_source, loop_video=s.loop_video).start()
    hub = Hub()
    hub.loop = asyncio.get_running_loop()
    hub_task = asyncio.create_task(hub.run())

    processor = None
    if detector is not None:
        processor = Processor(camera, detector, engine, store, s.target_fps, s.status_hz)
        processor.on_message = hub.publish_threadsafe
        processor.start()

    app.state.__dict__.update(settings=s, store=store, camera=camera, hub=hub,
                              processor=processor, model_error=model_error)
    log.info("Check backend %s started (detector=%s, camera=%s)", __version__, s.detector,
             s.camera_source)
    yield
    if processor:
        processor.stop()
    camera.stop()
    hub_task.cancel()


app = FastAPI(title="Check backend", version=__version__, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    st = app.state
    p = st.processor
    _, frame_t = st.camera.read()
    return {
        "ok": p is not None and st.camera.connected and (p.last_error is None),
        "version": __version__,
        "camera": {"source": st.settings.camera_source, "connected": st.camera.connected,
                   "last_frame_age_s": round(time.time() - frame_t, 2) if frame_t else None},
        "model": {"detector": st.settings.detector, "loaded": p is not None,
                  "error": st.model_error},
        "fps": round(p.fps, 1) if p else 0.0,
        "error": p.last_error if p else st.model_error,
    }


@app.get("/stream")
async def stream():
    p = app.state.processor
    if p is None:
        raise HTTPException(503, "detector not loaded")
    dt = 1.0 / max(app.state.settings.target_fps, 1.0)

    async def frames():
        last = None
        while True:
            jpg = p.latest_jpeg
            if jpg is not None and jpg is not last:
                last = jpg
                yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                       + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
            await asyncio.sleep(dt / 2)

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-cache"})


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    hub: Hub = app.state.hub
    hub.clients.add(websocket)
    p = app.state.processor
    await websocket.send_json({"type": "status", "people": p.latest_status if p else [],
                               "fps": round(p.fps, 1) if p else 0.0})
    try:
        while True:
            await websocket.receive_text()  # keep-alive / ignore client messages
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(websocket)


@app.get("/events")
def events(limit: int = Query(50, ge=1, le=500)):
    return app.state.store.recent(limit)


@app.get("/snapshots/{event_id}.jpg")
def snapshot(event_id: str):
    if not EVENT_ID.match(event_id):
        raise HTTPException(400, "bad event id")
    path = app.state.store.snapshot_path(event_id)
    if not path.exists():
        raise HTTPException(404, "snapshot not found")
    return FileResponse(path, media_type="image/jpeg")
