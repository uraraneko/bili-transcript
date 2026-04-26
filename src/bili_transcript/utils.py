from __future__ import annotations

import re
import shutil
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[\\/:*?\"<>|]+", "_", value)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "untitled"


def format_timestamp(seconds: float, srt: bool = False) -> str:
    total_ms = max(int(round(seconds * 1000)), 0)
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    sep = "," if srt else "."
    return f"{hours:02}:{minutes:02}:{secs:02}{sep}{millis:03}"


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"Missing required binary: {name}")
    return path
