from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

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

_STEP_PENDING = "pending"
_STEP_RUNNING = "running"
_STEP_DONE = "done"
_STEP_SKIP = "skip"
_STEP_ERROR = "error"


class StepTracker:
    def __init__(self, steps: list[str]) -> None:
        self._steps: list[dict[str, Any]] = [
            {"label": s, "state": _STEP_PENDING, "detail": ""} for s in steps
        ]
        self._spinner = Spinner("dots")

    def start(self, index: int) -> None:
        self._steps[index]["state"] = _STEP_RUNNING

    def done(self, index: int, detail: str = "") -> None:
        self._steps[index]["state"] = _STEP_DONE
        self._steps[index]["detail"] = detail

    def skip(self, index: int, detail: str = "") -> None:
        self._steps[index]["state"] = _STEP_SKIP
        self._steps[index]["detail"] = detail

    def error(self, index: int, detail: str = "") -> None:
        self._steps[index]["state"] = _STEP_ERROR
        self._steps[index]["detail"] = detail

    def render(self) -> Table:
        table = Table.grid(padding=(0, 1))
        table.add_column(width=3)
        table.add_column(min_width=20)
        table.add_column()
        for step in self._steps:
            state = step["state"]
            if state == _STEP_PENDING:
                icon: Any = Text("○", style="dim")
            elif state == _STEP_RUNNING:
                icon = self._spinner
            elif state == _STEP_DONE:
                icon = Text("✓", style="bold green")
            elif state == _STEP_SKIP:
                icon = Text("‒", style="dim")
            else:
                icon = Text("✗", style="bold red")

            label_style = "bold" if state == _STEP_RUNNING else ("dim" if state == _STEP_PENDING else "")
            detail_style = "dim" if state != _STEP_ERROR else "red"
            table.add_row(
                icon,
                Text(step["label"], style=label_style),
                Text(str(step["detail"]), style=detail_style),
            )
        return table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bili-transcript",
        description="下载 B 站视频字幕或转写音频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n  bili-transcript BV1w7NTzXEqQ\n  bili-transcript https://www.bilibili.com/video/BV1w7NTzXEqQ/",
    )
    parser.add_argument("input", nargs="?", help="Bilibili 链接 或 BV 号")
    parser.add_argument(
        "-f",
        "--format",
        choices=["txt", "srt", "json", "all"],
        default="all",
        help="输出格式（默认：all）",
    )
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help="Whisper 模型大小")
    parser.add_argument("-l", "--lang", default=DEFAULT_LANGUAGE, help="语言，默认自动检测")
    parser.add_argument("-o", "--output", default=None, help="输出目录（默认：./output）")
    parser.add_argument("--temp-dir", default=str(DEFAULT_TEMP_DIR), help="临时文件目录")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="Whisper 计算设备")
    parser.add_argument(
        "--cookies-from-browser",
        default="chrome",
        help="从浏览器读取 Cookie（默认：chrome）",
    )
    parser.add_argument("--force-whisper", action="store_true", help="忽略 B 站字幕，强制 Whisper 转写")
    parser.add_argument("--keep-audio", action="store_true", help="保留下载的音频文件")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.input:
        console.print("[bold red]错误：未提供视频链接或 BV 号[/bold red]")
        console.print()
        parser.print_help()
        raise SystemExit(1)

    output_hint = args.output or str(DEFAULT_OUTPUT_DIR)

    steps = [
        "解析链接",
        "获取视频信息",
        "提取 B 站字幕",
        "下载音频",
        "音频转码 (WAV)",
        "Whisper 转写",
        f"导出文件 → {output_hint}",
    ]

    STEP_PARSE = 0
    STEP_FETCH = 1
    STEP_SUBTITLE = 2
    STEP_DOWNLOAD = 3
    STEP_CONVERT = 4
    STEP_TRANSCRIBE = 5
    STEP_EXPORT = 6

    tracker = StepTracker(steps)

    with Live(tracker.render(), console=console, refresh_per_second=12) as live:
        def refresh() -> None:
            live.update(tracker.render())

        try:
            tracker.start(STEP_PARSE)
            refresh()
            try:
                canonical_url, video_id = normalize_bilibili_url(args.input)
            except FetchError:
                tracker.error(STEP_PARSE, "无法识别的链接，请输入 B 站视频链接或 BV 号")
                refresh()
                raise SystemExit(1)
            tracker.done(STEP_PARSE, video_id)
            refresh()

            output_dir = ensure_dir(Path(args.output) if args.output else DEFAULT_OUTPUT_DIR)
            temp_dir = ensure_dir(Path(args.temp_dir))
            tracker._steps[STEP_EXPORT]["label"] = f"导出文件 → {output_dir.resolve()}"

            tracker.start(STEP_FETCH)
            refresh()
            try:
                info = fetch_video_info(canonical_url, args.cookies_from_browser)
            except FetchError as exc:
                tracker.error(STEP_FETCH, f"{exc}（检查网络或 Cookie 设置）")
                refresh()
                raise SystemExit(1)
            title = str(info.get("title") or video_id)
            uploader = str(info.get("uploader") or "")
            duration_val = info.get("duration")
            duration_str = ""
            if isinstance(duration_val, int | float):
                minutes, seconds = divmod(int(duration_val), 60)
                duration_str = f"{minutes}:{seconds:02d}"
            detail_parts = [p for p in [title, uploader, duration_str] if p]
            tracker.done(STEP_FETCH, "  ".join(detail_parts))
            refresh()

            subtitle_segments = None
            if args.force_whisper:
                tracker.skip(STEP_SUBTITLE, "已跳过（--force-whisper）")
                refresh()
            else:
                tracker.start(STEP_SUBTITLE)
                refresh()
                subtitle_segments = extract_subtitle_segments(info, args.cookies_from_browser)
                if subtitle_segments:
                    tracker.done(STEP_SUBTITLE, f"{len(subtitle_segments)} 条")
                    refresh()
                else:
                    tracker.skip(STEP_SUBTITLE, "未找到，将使用 Whisper 转写")
                    refresh()

            if subtitle_segments:
                tracker.skip(STEP_DOWNLOAD, "已跳过")
                tracker.skip(STEP_CONVERT, "已跳过")
                tracker.skip(STEP_TRANSCRIBE, "已跳过")
                refresh()
                meta = build_meta(info, canonical_url, video_id, "bilibili")
                result = TranscriptResult(meta=meta, segments=subtitle_segments)
            else:
                tracker.start(STEP_DOWNLOAD)
                refresh()
                try:
                    audio_path = download_audio(canonical_url, temp_dir, video_id, args.cookies_from_browser)
                except FetchError as exc:
                    tracker.error(STEP_DOWNLOAD, str(exc))
                    refresh()
                    raise SystemExit(1)
                tracker.done(STEP_DOWNLOAD, audio_path.name)
                refresh()

                tracker.start(STEP_CONVERT)
                refresh()
                wav_path = temp_dir / f"{video_id}.converted.wav"
                try:
                    convert_to_wav(audio_path, wav_path)
                except TranscriptionError as exc:
                    tracker.error(STEP_CONVERT, str(exc))
                    refresh()
                    raise SystemExit(1)
                tracker.done(STEP_CONVERT)
                refresh()

                tracker.start(STEP_TRANSCRIBE)
                refresh()
                try:
                    segments = transcribe_audio(wav_path, args.model, args.lang, args.device)
                except TranscriptionError as exc:
                    tracker.error(STEP_TRANSCRIBE, str(exc))
                    refresh()
                    raise SystemExit(1)
                tracker.done(STEP_TRANSCRIBE, f"{len(segments)} 条")
                refresh()

                meta = build_meta(info, canonical_url, video_id, "whisper")
                result = TranscriptResult(meta=meta, segments=segments)

                if not args.keep_audio:
                    for path in {audio_path, wav_path}:
                        if path.exists():
                            path.unlink()

            tracker.start(STEP_EXPORT)
            refresh()
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
            tracker.done(STEP_EXPORT, "  ".join(p.name for p in saved_paths))
            refresh()

        except SystemExit:
            raise
        except (FetchError, TranscriptionError, RuntimeError) as exc:
            console.print(f"\n[bold red]错误：{exc}[/bold red]")
            raise SystemExit(1) from exc
