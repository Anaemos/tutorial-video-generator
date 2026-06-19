import subprocess
import shutil


def record_screen(output_path: str, duration: int | None = None) -> subprocess.Popen:
    """Start screen recording in the background using ffmpeg.

    Returns immediately with the running process handle instead of
    blocking, so the caller can start it, do other work, and stop it
    later via stop_recording().
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise FileNotFoundError("ffmpeg not found. Please install ffmpeg and add it to PATH.")

    cmd = [
        ffmpeg_path,
        "-y",
        "-f", "gdigrab",
        "-framerate", "30",
        "-i", "desktop",
    ]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += ["-vcodec", "libx264", output_path]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,  # PIPE would deadlock on long recordings
        stderr=subprocess.DEVNULL,
    )
    return process


def stop_recording(process: subprocess.Popen, timeout: float = 10.0) -> None:
    """Stop a recording started by record_screen(), finalizing the file cleanly."""
    if process.poll() is not None:
        return  # already exited on its own

    try:
        process.communicate(input=b"q", timeout=timeout)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()