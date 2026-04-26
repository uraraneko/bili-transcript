import json

from bili_transcript.exporters import export_json, export_srt, export_txt
from bili_transcript.models import Segment, TranscriptResult, VideoMeta


def make_result() -> TranscriptResult:
    return TranscriptResult(
        meta=VideoMeta(
            video_id="BV1test",
            title="demo",
            source_url="https://www.bilibili.com/video/BV1test/",
            duration=10,
            uploader="tester",
            subtitle_source="bilibili",
        ),
        segments=[
            Segment(start=0.0, end=1.2, text="第一句"),
            Segment(start=1.2, end=2.5, text="第二句"),
        ],
    )


def test_export_txt(tmp_path) -> None:
    path = export_txt(make_result(), tmp_path / "demo.txt")
    assert path.read_text(encoding="utf-8") == "第一句\n第二句\n"


def test_export_srt(tmp_path) -> None:
    path = export_srt(make_result(), tmp_path / "demo.srt")
    content = path.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,200" in content
    assert "第二句" in content


def test_export_json(tmp_path) -> None:
    path = export_json(make_result(), tmp_path / "demo.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["meta"]["video_id"] == "BV1test"
    assert len(data["segments"]) == 2
