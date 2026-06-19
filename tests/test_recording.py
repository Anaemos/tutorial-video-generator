import os
import time

import pyautogui

from parser.parser import parse_script
from recording.vscode_automation import open_vscode, type_code
from recording.screen_recorder import record_screen, stop_recording

pyautogui.FAILSAFE = True


def test_run_tutorial():
    """End-to-end recording test using the real tutorial script's steps,
    instead of a separate hardcoded copy."""
    output_dir = "output/recordings"
    output_path = f"{output_dir}/calculator_tutorial.mp4"

    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)

    script = parse_script("input/calculator_script.md")

    print("Opening VS Code...")
    open_vscode("input/calculator.py")

    print("Starting screen recording...")
    recording = record_screen(output_path)

    try:
        time.sleep(2)
        print("Typing tutorial code...")
        for step in script.steps:
            type_code(step.code + "\n", delay_per_char=0.05)
            time.sleep(0.5)

        print("Running Python code...")
        pyautogui.hotkey('ctrl', '`')
        time.sleep(2)
        pyautogui.write("python input/calculator.py", interval=0.05)
        pyautogui.press('enter')
        time.sleep(5)
    finally:
        stop_recording(recording)

    assert os.path.exists(output_path), "Recording not found!"
    assert os.path.getsize(output_path) > 0, "Recording file is empty!"
    print("✅ Test passed! File saved at", output_path)


if __name__ == "__main__":
    test_run_tutorial()