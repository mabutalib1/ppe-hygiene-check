"""Download the model and demo video at startup when they aren't in the image.

Weights and footage are not in git, so a cloud host (Render) gets them from
GitHub Releases: set WEIGHTS_URL / CAMERA_SOURCE_URL and the file is fetched to
the WEIGHTS / CAMERA_SOURCE path once (skipped when it already exists).
"""
from __future__ import annotations

import logging
import shutil
import urllib.request
from pathlib import Path

log = logging.getLogger("check.assets")


def fetch(url: str, dest: str | Path, timeout: float = 60.0) -> Path:
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    log.info("downloading %s -> %s", url, dest)
    with urllib.request.urlopen(url, timeout=timeout) as r, tmp.open("wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    tmp.replace(dest)  # never leave a half file behind under the real name
    log.info("downloaded %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
    return dest


def fetch_all(settings) -> None:
    if settings.weights_url:
        fetch(settings.weights_url, settings.weights)
    if settings.camera_source_url:
        fetch(settings.camera_source_url, settings.camera_source)
