# bili-transcript

B站视频字幕提取与转写工具。

## 技术框架设计（脚本版）

- 运行环境：uv + Python 3.12
- 入口层：CLI 脚本，输入 B站 URL/BV 号
- 采集层：yt-dlp 获取视频信息、字幕、音频流
- 转码层：ffmpeg 提取/转为标准 wav
- 识别层：优先读取现成字幕；无字幕则用 faster-whisper 转写
- 输出层：生成 txt / srt / json
- 可选增强：pydantic（配置/数据模型）、rich/typer（CLI 体验）、httpx（补充请求）

## 技术栈

- uv
- Python 3.12
- yt-dlp
- ffmpeg
- faster-whisper
- 可选：typer、rich、pydantic、httpx

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
