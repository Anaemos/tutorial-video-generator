from recording.screen_recorder import record_screen
import os

def test_record_screen():
    result = record_screen("output/recordings/test.mp4", duration=5)
    assert result is not None
    assert os.path.exists(result)
