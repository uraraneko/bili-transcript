from __future__ import annotations

import json
from pathlib import Path

from bili_transcript.models import TranscriptResult
from bili_transcript.utils import format_timestamp


def export_txt(result: TranscriptResult, output_path: Path) -> Path:
    lines = [segment.text.strip() for segment in result.segments if segment.text.strip()]
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output_path


def export_srt(result: TranscriptResult, output_path: Path) -> Path:
    chunks: list[str] = []
    for index, segment in enumerate(result.segments, start=1):
        text = segment.text.strip()
        if not text:
            continue
        chunks.append(str(index))
        chunks.append(
            f"{format_timestamp(segment.start, srt=True)} --> {format_timestamp(segment.end, srt=True)}"
        )
        chunks.append(text)
        chunks.append("")
    output_path.write_text("\n".join(chunks), encoding="utf-8")
    return output_path


def export_json(result: TranscriptResult, output_path: Path) -> Path:
    output_path.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path
