from assembly.merge_video import merge_audio_video
from assembly.subtitle_overlay import add_subtitles
import os

def test_merge_audio_video():
    result = merge_audio_video(
        "output/recordings/test.mp4",
        "output/audio/test.mp3",
        "output/recordings/merged.mp4"
    )
    assert result is not None
    assert os.path.exists(result)

def test_add_subtitles():
    result = add_subtitles(
        "output/recordings/merged.mp4",
        "output/subtitles/test.srt",
        "output/final/test.mp4"
    )
    assert result is not None
    assert os.path.exists(result)
