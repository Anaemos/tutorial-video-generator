"""Integration contract for the assembly module.

Generates its own dummy video / audio / srt so it runs standalone, without
depending on any other module's output (Rule 3). Run with: pytest tests/
"""

import os
import shutil
import subprocess

import pytest

from assembly.merge_video import merge_audio_video
from assembly.subtitle_overlay import add_subtitles

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg is required for assembly integration tests",
)


def _make_dummy_video(path: str, duration: int = 3) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"color=c=blue:s=640x480:d={duration}",
         "-pix_fmt", "yuv420p", path],
        check=True, capture_output=True, timeout=30,
    )


def _make_dummy_audio(path: str, duration: int = 3) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"sine=frequency=440:duration={duration}", path],
        check=True, capture_output=True, timeout=30,
    )


def _make_dummy_srt(path: str) -> None:
    with open(path, "w") as f:
        f.write(
            "1\n00:00:00,000 --> 00:00:01,500\nHello world\n\n"
            "2\n00:00:01,500 --> 00:00:03,000\nTesting subtitles\n"
        )


def test_merge_audio_video(tmp_path):
    video = str(tmp_path / "screen.mp4")
    audio = str(tmp_path / "narration.mp3")
    out = str(tmp_path / "merged.mp4")
    _make_dummy_video(video)
    _make_dummy_audio(audio)

    result = merge_audio_video(video, audio, out)

    assert os.path.isfile(result)
    assert os.path.getsize(result) > 0


def test_add_subtitles(tmp_path):
    video = str(tmp_path / "screen.mp4")
    audio = str(tmp_path / "narration.mp3")
    merged = str(tmp_path / "merged.mp4")
    srt = str(tmp_path / "subs.srt")
    out = str(tmp_path / "final.mp4")
    _make_dummy_video(video)
    _make_dummy_audio(audio)
    merge_audio_video(video, audio, merged)
    _make_dummy_srt(srt)

    result = add_subtitles(merged, srt, out)

    assert os.path.isfile(result)
    assert os.path.getsize(result) > 0