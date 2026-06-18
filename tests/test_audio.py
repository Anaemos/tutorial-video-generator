from audio.tts import generate_tts
from audio.subtitles import generate_subtitles

def test_audio():
    path = generate_tts("Hello, this is a test.", "output/audio/test.mp3")
    assert path.endswith(".mp3")
    print("TTS works")

def test_subtitles():
    path = generate_subtitles("output/audio/test.mp3", "output/subtitles/test.srt")
    assert path.endswith(".srt")
    print("Subtitles work")

if __name__ == "__main__":
    test_audio()
    test_subtitles()