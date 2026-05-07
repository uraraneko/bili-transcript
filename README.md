# bili-transcript

B站视频字幕提取与转写工具。

## 技术框架设计（脚本版）

- 运行环境：uv + Python 3.12
- 入口层：CLI 脚本，输入 B站 URL/BV 号
- 采集层：yt-dlp 获取视频信息、字幕、音频流
- 转码层：ffmpeg 提取/转为标准 wav
- 识别层：优先读取现成字幕；无字幕则用 faster-whisper 转写
- 输出层：生成 txt / srt / json

## 技术栈

- uv
- Python 3.12
- yt-dlp
- ffmpeg
- faster-whisper

## 安装

1. 安装系统依赖：`ffmpeg`
2. 安装 Python 依赖：

```bash
uv sync
```

## 使用

```bash
uv run bili-transcript --help
uv run bili-transcript "https://www.bilibili.com/video/BV1UyDzBpEeo/"
uv run bt "https://www.bilibili.com/video/BV1UyDzBpEeo/"
```

## 其他常用命令

最简用法：

```bash
uv run bili-transcript "https://www.bilibili.com/video/BV1UyDzBpEeo/" --cookies-from-browser chrome
```

输出全部格式：

```bash
uv run bili-transcript "https://www.bilibili.com/video/BV1UyDzBpEeo/" -f all -o "./output" --cookies-from-browser chrome
```

强制走音频转写：

```bash
uv run bili-transcript "https://www.bilibili.com/video/BV1UyDzBpEeo/" --force-whisper --cookies-from-browser chrome
```

## 常用参数

- `-f, --format`：输出格式，可选 `txt`、`srt`、`json`、`all`
- `-o, --output`：输出目录
- `--cookies-from-browser`：从浏览器读取 cookies，例如 `chrome`
- `--force-whisper`：忽略现成字幕，强制下载音频并转写
- `-m, --model`：Whisper 模型大小，如 `base`、`small`
- `-l, --lang`：识别语言，默认 `auto`

## AI Skill

本项目附带一个 AI agent skill（`.skills/fetching-bilibili-transcripts/`），可让 AI 编码助手（如 CodeFlicker/KwaiPilot）自动识别用户意图并调用本工具获取 B 站视频文字稿。将 skill 目录复制到 `~/.agents/skills/` 即可启用。
