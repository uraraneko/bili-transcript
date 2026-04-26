from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

from faster_whisper import WhisperModel  # type: ignore[import-untyped]

from bili_transcript.config import SAMPLE_RATE
from bili_transcript.models import Segment
from bili_transcript.utils import require_binary


class TranscriptionError(RuntimeError):
    pass


def convert_to_wav(audio_path: Path, wav_path: Path) -> Path:
    if audio_path.resolve() == wav_path.resolve():
        return wav_path
    ffmpeg = require_binary("ffmpeg")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(audio_path),
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-vn",
        str(wav_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise TranscriptionError(result.stderr.strip() or "ffmpeg convert failed")
    return wav_path


def transcribe_audio(
    wav_path: Path,
    model_size: str,
    language: str,
    device: str,
) -> list[Segment]:
    try:
        model = WhisperModel(model_size, device="cpu" if device == "auto" else device)
        segments_iter, _info = model.transcribe(
            str(wav_path),
            language=None if language == "auto" else language,
            vad_filter=True,
        )
    except Exception as exc:  # noqa: BLE001
        raise TranscriptionError(str(exc)) from exc

    segments: list[Segment] = []
    for segment in segments_iter:
        text = cast(str, segment.text).strip()
        if not text:
            continue
        start = float(cast(float, segment.start))
        end = float(cast(float, segment.end))
        segments.append(Segment(start=start, end=max(end, start), text=text))
    return segments
