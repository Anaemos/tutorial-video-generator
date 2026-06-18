import os
import threading
import time
import pyautogui

from recording.vscode_automation import open_vscode, type_code
from recording.screen_recorder import record_screen

pyautogui.FAILSAFE = True

TUTORIAL_STEPS = [
    ("# Calculator Tutorial by Python Teacher\n", 1),
    ("\n", 0.5),
    ("def add(a, b):\n", 1),
    ("    return a + b\n", 1),
    ("\n", 0.5),
    ("def subtract(a, b):\n", 1),
    ("    return a - b\n", 1),
    ("\n", 0.5),
    ("def multiply(a, b):\n", 1),
    ("    return a * b\n", 1),
    ("\n", 0.5),
    ("def divide(a, b):\n", 1),
    ("    if b == 0:\n", 1),
    ("        return 'Error: Division by zero'\n", 1),
    ("    return a / b\n", 1),
    ("\n", 0.5),
    ("print(add(10, 5))\n", 0.5),
    ("print(subtract(10, 5))\n", 0.5),
    ("print(multiply(10, 5))\n", 0.5),
    ("print(divide(10, 5))\n", 1),
]


def run_tutorial():
    output_dir = "output/recordings"
    output_path = f"{output_dir}/calculator_tutorial.mp4"

    os.makedirs(output_dir, exist_ok=True)

    print("Opening VS Code...")
    open_vscode("input/calculator.py")

    print("Starting screen recording...")
    recorder = threading.Thread(
        target=record_screen,
        args=(output_path,),
        kwargs={"duration": 90}
    )
    recorder.start()

    time.sleep(2)

    print("Typing tutorial code...")
    for code, pause in TUTORIAL_STEPS:
        type_code(code, delay_per_char=0.05)
        time.sleep(pause)

    print("Running Python code...")
    pyautogui.hotkey('ctrl', '`')
    time.sleep(2)

    pyautogui.write("python input/calculator.py", interval=0.05)
    pyautogui.press('enter')

    time.sleep(5)
    recorder.join()

    if os.path.exists(output_path):
        print("✅ Video created successfully!")
        print(output_path)
    else:
        print("❌ Recording failed")


if __name__ == "__main__":
    run_tutorial()