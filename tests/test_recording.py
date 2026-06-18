import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from recording.vscode_automation import open_vscode, type_code
from recording.screen_recorder import record_screen

def test_recording():
    print("Starting screen recording for 10 seconds...")
    record_screen("output/recordings/test_screen.mp4", duration=10)

    print("Opening VS Code...")
    open_vscode("input/sample_tutorial.md")

    print("Typing code...")
    type_code("print('hello world')", delay_per_char=0.05)

    # Check output file exists
    assert os.path.exists("output/recordings/test_screen.mp4"), "Recording not found!"
    print("✅ Test passed! File saved at output/recordings/test_screen.mp4")

test_recording()