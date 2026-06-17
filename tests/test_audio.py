from audio.tts import generate_tts
from audio.subtitles import generate_subtitles
import os

def test_generate_tts():
    result = generate_tts("hello world", "output/audio/test.mp3")
    assert result is not None
    assert os.path.exists(result)

def test_generate_subtitles():
    result = generate_subtitles("output/audio/test.mp3", "output/subtitles/test.srt")
    assert result is not None
    assert os.path.exists(result)
