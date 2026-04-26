from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from bili_transcript.models import Segment, VideoMeta

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)


class FetchError(RuntimeError):
    pass


def normalize_bilibili_url(value: str) -> tuple[str, str]:
    candidate = value.strip()
    bv_match = re.search(r"(BV[0-9A-Za-z]+)", candidate)
    if bv_match:
        video_id = bv_match.group(1)
        return f"https://www.bilibili.com/video/{video_id}/", video_id
    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc and "bilibili.com" in parsed.netloc:
        path_match = re.search(r"/(BV[0-9A-Za-z]+)/?", parsed.path)
        if path_match:
            video_id = path_match.group(1)
            return f"https://www.bilibili.com/video/{video_id}/", video_id
    raise FetchError("Invalid bilibili URL or BV id")


def _base_ydl_options(cookies_from_browser: str | None = None) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "skip_download": True,
        "http_headers": {
            "Referer": "https://www.bilibili.com/",
            "User-Agent": DEFAULT_USER_AGENT,
        },
    }
    if cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)
    return options


def fetch_video_info(url: str, cookies_from_browser: str | None = None) -> dict[str, object]:
    try:
        with YoutubeDL(_base_ydl_options(cookies_from_browser)) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        raise FetchError(str(exc)) from exc
    if not isinstance(info, dict):
        raise FetchError("Unable to fetch video info")
    return cast(dict[str, object], info)


def build_meta(info: dict[str, object], source_url: str, video_id: str, subtitle_source: str) -> VideoMeta:
    duration_value = info.get("duration")
    duration = float(duration_value) if isinstance(duration_value, int | float | str) else None
    return VideoMeta(
        video_id=video_id,
        title=str(info.get("title") or video_id),
        source_url=source_url,
        duration=duration,
        uploader=str(info.get("uploader")) if info.get("uploader") else None,
        subtitle_source=subtitle_source,
    )


def _subtitle_languages(info: dict[str, object]) -> list[dict[str, object]]:
    subtitles = info.get("subtitles")
    automatic = info.get("automatic_captions")
    sources: list[dict[str, object]] = []
    if isinstance(subtitles, dict):
        sources.append(subtitles)
    if isinstance(automatic, dict):
        sources.append(automatic)
    return sources


def extract_subtitle_segments(
    info: dict[str, object], cookies_from_browser: str | None = None
) -> list[Segment] | None:
    for source in _subtitle_languages(info):
        for language in ("zh-Hans", "zh-CN", "zh", "en"):
            entries = source.get(language)
            if isinstance(entries, list):
                segments = _download_subtitle_entries(entries, cookies_from_browser)
                if segments:
                    return segments
        for entries in source.values():
            if isinstance(entries, list):
                segments = _download_subtitle_entries(entries, cookies_from_browser)
                if segments:
                    return segments
    return None


def _download_subtitle_entries(
    entries: list[object], cookies_from_browser: str | None = None
) -> list[Segment] | None:
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        ext = entry.get("ext")
        if isinstance(url, str) and ext in {"json", "vtt", "srt", "srv3"}:
            return _parse_remote_subtitle(url, str(ext), cookies_from_browser)
    return None


def _parse_remote_subtitle(
    url: str, ext: str, cookies_from_browser: str | None = None
) -> list[Segment]:
    with YoutubeDL(_base_ydl_options(cookies_from_browser)) as ydl:  # type: ignore[arg-type]
        response = ydl.urlopen(url)
        raw = response.read().decode("utf-8", errors="ignore")
    if ext == "json":
        return _parse_json_subtitle(raw)
    if ext == "srt":
        return _parse_srt_subtitle(raw)
    return _parse_vtt_like_subtitle(raw)


def _parse_json_subtitle(raw: str) -> list[Segment]:
    data = json.loads(raw)
    body = data.get("body", []) if isinstance(data, dict) else []
    segments: list[Segment] = []
    for item in body:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        start = float(item.get("from") or 0.0)
        end = float(item.get("to") or start)
        segments.append(Segment(start=start, end=max(end, start), text=content))
    return segments


def _parse_vtt_like_subtitle(raw: str) -> list[Segment]:
    segments: list[Segment] = []
    blocks = re.split(r"\n\s*\n", raw.replace("\r\n", "\n"))
    time_pattern = re.compile(
        r"(?P<start>\d{2}:\d{2}:\d{2}[\.,]\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}[\.,]\d{3})"
    )
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        match_line = next((line for line in lines if time_pattern.search(line)), None)
        if match_line is None:
            continue
        match = time_pattern.search(match_line)
        if match is None:
            continue
        text_lines = [line for line in lines if line != match_line and not line.isdigit() and line != "WEBVTT"]
        text = " ".join(text_lines).strip()
        if not text:
            continue
        segments.append(
            Segment(
                start=_parse_timestamp(match.group("start")),
                end=_parse_timestamp(match.group("end")),
                text=text,
            )
        )
    return segments


def _parse_srt_subtitle(raw: str) -> list[Segment]:
    return _parse_vtt_like_subtitle(raw)


def _parse_timestamp(value: str) -> float:
    normalized = value.replace(",", ".")
    hours, minutes, rest = normalized.split(":")
    seconds, millis = rest.split(".")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def download_audio(
    url: str, temp_dir: Path, video_id: str, cookies_from_browser: str | None = None
) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_template = temp_dir / f"{video_id}.%(ext)s"
    options = _base_ydl_options(cookies_from_browser)
    options.update(
        {
            "skip_download": False,
            "format": "bestaudio/best",
            "outtmpl": str(output_template),
        }
    )
    before = {path.name for path in temp_dir.iterdir()}
    try:
        with YoutubeDL(options) as ydl:  # type: ignore[arg-type]
            ydl.download([url])
    except DownloadError as exc:
        raise FetchError(str(exc)) from exc
    after = {path.name for path in temp_dir.iterdir()}
    new_files = sorted((temp_dir / name for name in after - before), key=lambda path: path.stat().st_mtime)
    if not new_files:
        matches = sorted(temp_dir.glob(f"{video_id}.*"), key=lambda path: path.stat().st_mtime)
        if matches:
            return matches[-1]
        raise FetchError("Audio download failed")
    return new_files[-1]
