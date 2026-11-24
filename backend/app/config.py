"""All settings come from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env loader (KEY=VALUE, '#' comments). Real env vars win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.split(" #", 1)[0].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env(name: str, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    if isinstance(default, bool):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return type(default)(raw)


@dataclass
class EngineConfig:
    """Violation logic. Starting values from the plan; tune on the event clips."""
    item_conf: float = 0.40          # item boxes below this are ignored
    window_s: float = 3.0            # memory window per person per item
    violation_ratio: float = 0.70    # share of visible frames saying "not wearing"
    ok_ratio: float = 0.50           # share of visible frames saying "wearing"
    min_visibility: float = 0.40     # item must be seen in this share of the window
    decide_after_s: float = 3.0      # a new person needs this much history before any decision
    cooldown_s: float = 30.0         # one alert per person per item per cooldown
    assign_min_overlap: float = 0.50 # item box must be this much inside a person box
    lost_after_s: float = 1.5        # person unseen this long → considered lost
    reentry_s: float = 10.0          # a new track near a lost one within this time inherits it
    reentry_dist: float = 0.15       # max center distance, as a fraction of the frame diagonal

    @classmethod
    def from_env(cls) -> "EngineConfig":
        c = cls()
        for f in c.__dataclass_fields__:
            setattr(c, f, _env(f"CHECK_{f.upper()}", getattr(c, f)))
        return c


@dataclass
class Settings:
    camera_source: str = "0"           # RTSP/HTTP URL, webcam index, video file, or "synthetic"
    camera_name: str = "kitchen-1"
    detector: str = "yolo"             # "yolo" or "fake" (scripted detections, no model needed)
    weights: str = "weights/best.pt"
    device: str = ""                   # "" = auto, "cpu", "0" for first GPU
    imgsz: int = 640
    target_fps: float = 10.0
    loop_video: bool = True            # replay video files (demo backup)
    data_dir: Path = Path("runtime")
    status_hz: float = 2.0
    engine: EngineConfig = field(default_factory=EngineConfig)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        s = cls()
        s.camera_source = _env("CAMERA_SOURCE", s.camera_source)
        s.camera_name = _env("CAMERA_NAME", s.camera_name)
        s.detector = _env("DETECTOR", s.detector)
        s.weights = _env("WEIGHTS", s.weights)
        s.device = _env("DEVICE", s.device)
        s.imgsz = _env("IMGSZ", s.imgsz)
        s.target_fps = _env("TARGET_FPS", s.target_fps)
        s.loop_video = _env("LOOP_VIDEO", s.loop_video)
        s.data_dir = Path(_env("DATA_DIR", str(s.data_dir)))
        s.status_hz = _env("STATUS_HZ", s.status_hz)
        s.engine = EngineConfig.from_env()
        return s

    @property
    def db_path(self) -> Path:
        return self.data_dir / "events.db"

    @property
    def snapshot_dir(self) -> Path:
        return self.data_dir / "snapshots"
