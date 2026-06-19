import subprocess
import time
import os
import shutil

import pyautogui

pyautogui.FAILSAFE = True


def _find_vscode_path() -> str:
    """Locate the VS Code executable in a way that works across machines."""
    env_path = os.environ.get("VSCODE_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    which_path = shutil.which("code") or shutil.which("code.cmd")
    if which_path:
        return which_path

    raise FileNotFoundError(
        "Could not locate VS Code. Set the VSCODE_PATH environment variable "
        "to the Code executable path, or ensure 'code' is on your PATH."
    )


def _focus_vscode_window() -> None:
    """Bring the VS Code window to the foreground (replaces hardcoded click coords)."""
    try:
        windows = pyautogui.getWindowsWithTitle("Visual Studio Code")
        if windows:
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.5)
            return
    except Exception:
        pass

    screen_width, screen_height = pyautogui.size()
    pyautogui.click(screen_width // 2, screen_height // 2)
    time.sleep(0.5)


def open_vscode(filepath: str) -> None:
    """Open VS Code with given file."""
    code_path = _find_vscode_path()
    abs_filepath = os.path.abspath(filepath)
    subprocess.Popen([code_path, abs_filepath])

    time.sleep(6)
    _focus_vscode_window()

    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.5)
    pyautogui.press('backspace')
    time.sleep(1)


def type_code(code: str, delay_per_char: float = 0.05) -> None:
    """Type code in active editor."""
    _focus_vscode_window()
    pyautogui.write(code, interval=delay_per_char)