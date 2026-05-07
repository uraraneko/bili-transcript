# CLI Reference

## Full Parameter List

```
bili-transcript [INPUT] [OPTIONS]

Positional:
  INPUT                Bilibili URL or BV号 (required)

Options:
  -f, --format         Output format: txt, srt, json, all (default: all)
  -m, --model          Whisper model: base, small, medium, large (default: base)
  -l, --lang           Language for Whisper: auto, zh, en, ja, ko, etc (default: auto)
  -o, --output         Output directory path (default: ./output)
  --temp-dir           Temp directory for audio files (default: ./temp)
  --device             Compute device: auto, cpu, cuda (default: auto)
  --cookies-from-browser  Browser name for cookie extraction (default: chrome)
  --force-whisper      Skip subtitle extraction, force Whisper transcription
  --keep-audio         Keep downloaded audio files after transcription
```

Short alias: `bt` (identical functionality)

## Input Formats

The tool accepts:
- **BV号**: `BV1w7NTzXEqQ`
- **Full URL**: `https://www.bilibili.com/video/BV1w7NTzXEqQ/`
- **Short URL**: Any bilibili.com URL containing a BV号

The tool normalizes all inputs to a canonical URL and extracts the BV号.

## Whisper Model Sizes

| Model | Speed | Accuracy | Memory |
|-------|-------|----------|--------|
| base  | Fast  | Moderate | ~1GB   |
| small | Medium| Good     | ~2GB   |
| medium| Slow  | Very Good| ~5GB   |
| large | Very Slow| Best  | ~10GB  |

`base` is sufficient for most Chinese/English content. Use `small` or `medium` for higher accuracy.

## Cookie Extraction

Bilibili requires authentication cookies for most videos. The tool reads cookies from your browser using yt-dlp's `cookiesfrombrowser` feature.

Supported browsers: `chrome`, `firefox`, `edge`, `safari`, `opera`, `brave`

If cookie extraction fails:
1. Ensure the browser has an active Bilibili login session
2. Try a different browser: `--cookies-from-browser firefox`
3. On macOS, Safari may require keychain access permission

## Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| "无法识别的链接" | Invalid URL/BV号 | Provide valid BV号 or bilibili.com URL |
| "检查网络或 Cookie 设置" | yt-dlp fetch failed | Check network; ensure browser cookies available |
| "ffmpeg convert failed" | ffmpeg not found | Install ffmpeg: `brew install ffmpeg` |
| Whisper transcription error | Model load failure | Check device setting; ensure sufficient RAM |

## Output File Naming

Files are named using the sanitized video title:
- `视频标题.txt`
- `视频标题.srt`
- `视频标题.json`

Special characters in titles are replaced with safe alternatives.

## Workflow Details

### Subtitle Priority

The tool tries B站内置字幕 first, checking:
1. Manual subtitles (`subtitles`) in zh-Hans, zh-CN, zh, en order
2. Auto-generated subtitles (`automatic_captions`) in same language order
3. Any available subtitle language as fallback

If subtitles exist → skip download/transcription → use subtitle text directly.

### Whisper Fallback

When no subtitles are found:
1. Download audio stream via yt-dlp
2. Convert to WAV (16kHz mono) via ffmpeg
3. Transcribe with faster-whisper (VAD filter enabled)
4. Clean up temp audio files (unless `--keep-audio`)

## Example Scenarios

### Get transcript for analysis (JSON format)

```bash
cd /Users/chenenci/Personal/bili-transcript
uv run bili-transcript "https://www.bilibili.com/video/BV1UyDzBpEeo/" -f json
```

Then read with: `cat output/视频标题.json`

### Get plain text for reading

```bash
cd /Users/chenenci/Personal/bili-transcript
uv run bili-transcript "BV1w7NTzXEqQ" -f txt
```

### Force transcription for videos with poor subtitles

```bash
cd /Users/chenenci/Personal/bili-transcript
uv run bili-transcript "BV1w7NTzXEqQ" --force-whisper -m small
```

### Batch processing pattern

For multiple videos, run sequentially:

```bash
cd /Users/chenenci/Personal/bili-transcript
uv run bili-transcript "BV1xxxx" -f txt
uv run bili-transcript "BV2xxxx" -f txt
uv run bili-transcript "BV3xxxx" -f txt
```