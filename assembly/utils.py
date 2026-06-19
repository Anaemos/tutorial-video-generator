"""Shared helpers for the assembly module.

Only used internally by merge_video.py and subtitle_overlay.py.
Importing within your own module folder is fine - Rule 1 only forbids
importing ACROSS modules (audio/recording/assembly).
"""

import os
import subprocess


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is callable on this machine."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def validate_file_exists(path: str) -> None:
    """Raise a clear error if an expected input file is missing."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"assembly: required input file not found -> {path}")


def get_video_duration(path: str) -> float:
    """Return duration of a media file in seconds (uses ffprobe)."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def escape_subtitle_path(path: str) -> str:
    """Make a path safe for ffmpeg's `subtitles=` filter.

    The subtitles filter parses its argument, so Windows drive colons and
    backslashes break it. Convert to forward slashes and escape the colon.
    On Linux/macOS this is a harmless no-op.
        C:\\Users\\x\\subs.srt  ->  C\\:/Users/x/subs.srt
    """
    p = os.path.abspath(path)
    p = p.replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def run_ffmpeg(cmd: list[str], timeout: int | None = None) -> None:
    """Run an ffmpeg command and surface its stderr on failure.

    timeout is in seconds; None means no limit. Note the subtitle-burn step
    re-encodes the whole video, so don't set a tight timeout there - long
    videos take minutes. The merge step is a fast copy and can use a short one.
    """
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as e:
        raise RuntimeError("ffmpeg binary not found on PATH") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            "ffmpeg timed out:\n"
            f"command: {' '.join(cmd)}\n"
            f"timeout: {timeout}s"
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "ffmpeg failed:\n"
            f"command: {' '.join(cmd)}\n"
            f"stderr:\n{e.stderr}"
        ) from e