import subprocess

def record_screen(output_path: str, duration: int) -> str:
    """Records the screen for given duration and saves as MP4."""
    subprocess.run([
        "ffmpeg",
        "-y",                  # overwrite if file exists
        "-f", "gdigrab",       # Windows screen capture
        "-framerate", "30",
        "-i", "desktop",
        "-t", str(duration),
        "-vcodec", "libx264",
        output_path
    ])
    return output_path