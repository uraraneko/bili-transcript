from bili_transcript.models import Segment, TranscriptResult, VideoMeta
from bili_transcript.utils import format_timestamp


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


def test_format_timestamp() -> None:
    assert format_timestamp(1.234) == "00:00:01.234"
    assert format_timestamp(1.234, srt=True) == "00:00:01,234"
