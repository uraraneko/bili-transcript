from __future__ import annotations

from pydantic import BaseModel, Field


class Segment(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str


class VideoMeta(BaseModel):
    video_id: str
    title: str
    source_url: str
    duration: float | None = Field(default=None, ge=0)
    uploader: str | None = None
    subtitle_source: str


class TranscriptResult(BaseModel):
    meta: VideoMeta
    segments: list[Segment]
