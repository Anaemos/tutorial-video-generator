import subprocess
import shutil

def record_screen(output_path: str, duration: int) -> str:
    """Records the screen for given duration and saves as MP4."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise FileNotFoundError("ffmpeg not found. Please install ffmpeg and add it to PATH.")
    
    subprocess.run([
        ffmpeg_path,
        "-y",
        "-f", "gdigrab",
        "-framerate", "30",
        "-i", "desktop",
        "-t", str(duration),
        "-vcodec", "libx264",
        output_path
    ])
    return output_path