---
name: fetching-bilibili-transcripts
description: Fetch Bilibili video transcripts (字幕/文字稿) using the bili-transcript CLI tool. Use when the user wants to extract text from a Bilibili video, get a video's subtitles/transcript, mentions "B站字幕", "bilibili transcript", "BV号转文字", or asks to read/watch a Bilibili video's content as text. Supports both subtitle extraction and Whisper-based audio transcription.
---

# Fetching Bilibili Transcripts

Retrieve text transcripts from Bilibili videos using the `bili-transcript` CLI tool (alias: `bt`).

## When to Use

- User wants text content from a Bilibili video URL or BV号
- User mentions "B站字幕", "bilibili transcript", "视频文字稿"
- User asks to read/analyze a Bilibili video's content as text

## Prerequisites

The tool requires:
1. **uv** - Python package manager (https://docs.astral.sh/uv/)
2. **ffmpeg** - System dependency for audio conversion
3. **faster-whisper** - Auto-installed via `uv sync` for audio transcription
4. **Cookies** - Bilibili requires browser cookies for access; default reads from Chrome

Install project dependencies:

```bash
cd /Users/chenenci/Personal/bili-transcript && uv sync
```

Verify ffmpeg is available:

```bash
ffmpeg -version
```

## Quick Start

```bash
cd /Users/chenenci/Personal/bili-transcript && uv run bili-transcript "BV1w7NTzXEqQ"
```

Or with full URL:

```bash
cd /Users/chenenci/Personal/bili-transcript && uv run bili-transcript "https://www.bilibili.com/video/BV1w7NTzXEqQ/"
```

The tool outputs files to `./output/` by default with three formats: `.txt`, `.srt`, `.json`.

## How It Works

1. **Parse input** — Accepts BV号 (e.g., `BV1w7NTzXEqQ`) or full bilibili.com URL
2. **Fetch video info** — Uses yt-dlp with browser cookies
3. **Try B站字幕** — First attempts to extract existing subtitles (优先B站内置字幕)
4. **Fallback to Whisper** — If no subtitles found, downloads audio and transcribes with faster-whisper
5. **Export files** — Generates txt/srt/json in output directory

## Output Formats

- **txt** — Plain text, no timestamps (适合阅读)
- **srt** — SubRip format with timestamps (适合字幕叠加)
- **json** — Structured data with metadata + segments (适合程序处理)

JSON structure: `{ "meta": { "video_id", "title", "source_url", "duration", "uploader", "subtitle_source" }, "segments": [ { "start", "end", "text" } ] }`

## Common Commands

```bash
# Only txt output (最简)
uv run bili-transcript "BV1w7NTzXEqQ" -f txt

# Custom output directory
uv run bili-transcript "BV1w7NTzXEqQ" -o ./my-output

# Force Whisper transcription (忽略B站字幕)
uv run bili-transcript "BV1w7NTzXEqQ" --force-whisper

# Specify Whisper model size
uv run bili-transcript "BV1w7NTzXEqQ" -m small

# Use cookies from a different browser
uv run bili-transcript "BV1w7NTzXEqQ" --cookies-from-browser firefox
```

## Important Notes

- Always `cd /Users/chenenci/Personal/bili-transcript` before running commands
- The short alias `bt` can be used instead of `bili-transcript`
- Cookies from browser are needed for most videos; default is `chrome`
- If cookie extraction fails, try specifying your browser explicitly with `--cookies-from-browser`
- Whisper transcription is slow; prefer letting the tool extract existing subtitles first

## Reading Output

After running the tool, read the output file to provide transcript content to the user:

```bash
# Read plain text transcript
cat output/视频标题.txt

# Or use the read_file tool on the json for structured data
```

## Troubleshooting

For detailed CLI parameters and troubleshooting, see [references/cli-reference.md](references/cli-reference.md).