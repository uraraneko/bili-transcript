from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from bili_transcript.config import (
    DEFAULT_DEVICE,
    DEFAULT_FORMATS,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TEMP_DIR,
)
from bili_transcript.exporters import export_json, export_srt, export_txt
from bili_transcript.fetcher import (
    FetchError,
    build_meta,
    download_audio,
    extract_subtitle_segments,
    fetch_video_info,
    normalize_bilibili_url,
)
from bili_transcript.models import TranscriptResult
from bili_transcript.transcriber import TranscriptionError, convert_to_wav, transcribe_audio
from bili_transcript.utils import ensure_dir, sanitize_filename

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bili-transcript")
    parser.add_argument("input", help="Bilibili URL or BV id")
    parser.add_argument(
        "-f",
        "--format",
        choices=["txt", "srt", "json", "all"],
        default="all",
        help="Output format",
    )
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help="Whisper model size")
    parser.add_argument("-l", "--lang", default=DEFAULT_LANGUAGE, help="Language, default auto")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    parser.add_argument("--temp-dir", default=str(DEFAULT_TEMP_DIR), help="Temporary directory")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="Whisper device")
    parser.add_argument("--cookies-from-browser", help="Browser name for yt-dlp cookies, e.g. chrome")
    parser.add_argument("--force-whisper", action="store_true", help="Ignore remote subtitles")
    parser.add_argument("--keep-audio", action="store_true", help="Keep downloaded audio and wav")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        canonical_url, video_id = normalize_bilibili_url(args.input)
        info = fetch_video_info(canonical_url, args.cookies_from_browser)
        output_dir = ensure_dir(Path(args.output))
        temp_dir = ensure_dir(Path(args.temp_dir))

        subtitle_segments = None if args.force_whisper else extract_subtitle_segments(
            info, args.cookies_from_browser
        )
        if subtitle_segments:
            meta = build_meta(info, canonical_url, video_id, "bilibili")
            result = TranscriptResult(meta=meta, segments=subtitle_segments)
        else:
            audio_path = download_audio(canonical_url, temp_dir, video_id, args.cookies_from_browser)
            wav_path = temp_dir / f"{video_id}.converted.wav"
            convert_to_wav(audio_path, wav_path)
            segments = transcribe_audio(wav_path, args.model, args.lang, args.device)
            meta = build_meta(info, canonical_url, video_id, "whisper")
            result = TranscriptResult(meta=meta, segments=segments)
            if not args.keep_audio:
                for path in {audio_path, wav_path}:
                    if path.exists():
                        path.unlink()

        base_name = sanitize_filename(result.meta.title or result.meta.video_id)
        formats = DEFAULT_FORMATS if args.format == "all" else (args.format,)
        saved_paths: list[Path] = []
        for fmt in formats:
            destination = output_dir / f"{base_name}.{fmt}"
            if fmt == "txt":
                saved_paths.append(export_txt(result, destination))
            elif fmt == "srt":
                saved_paths.append(export_srt(result, destination))
            elif fmt == "json":
                saved_paths.append(export_json(result, destination))

        console.print(f"source={result.meta.subtitle_source}")
        for path in saved_paths:
            console.print(str(path))
    except (FetchError, TranscriptionError, RuntimeError) as exc:
        console.print(f"error: {exc}", style="red")
        raise SystemExit(1) from exc
