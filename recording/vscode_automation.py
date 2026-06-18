import subprocess
import pyautogui
import time
import os

pyautogui.FAILSAFE = True

def open_vscode(filepath: str) -> None:
    """Open VS Code with given file."""
    code_path = r"C:\Users\patel\AppData\Local\Programs\Microsoft VS Code\Code.exe"

    if not os.path.exists(code_path):
        raise FileNotFoundError(f"VS Code not found at: {code_path}")

    abs_filepath = os.path.abspath(filepath)
    subprocess.Popen([code_path, abs_filepath])

    # Wait for VS Code to open
    time.sleep(6)

    # Click editor area (adjust if needed)
    pyautogui.click(700, 350)
    time.sleep(1)

    # Clear existing content
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.5)
    pyautogui.press('backspace')
    time.sleep(1)


def type_code(code: str, delay_per_char: float = 0.05) -> None:
    """Type code in active editor."""
    for char in code:
        pyautogui.write(char, interval=delay_per_char)