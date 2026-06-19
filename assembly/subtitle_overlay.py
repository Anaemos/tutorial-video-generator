"""Step 2 of assembly: burn the SRT captions into the video. Final step."""

from assembly.utils import validate_file_exists, run_ffmpeg, escape_subtitle_path


def add_subtitles(video_path: str, srt_path: str, output_path: str) -> str:
    """Burn SRT captions into the video as permanently visible text.

    Burning (hardsubbing) requires re-encoding the video stream; the audio
    is copied through untouched. Returns the path to the final video.
    """
    validate_file_exists(video_path)
    validate_file_exists(srt_path)

    srt = escape_subtitle_path(srt_path)

    # Optional readable styling. Drop the :force_style=... part for plain subs.
    style = "FontSize=22,Outline=1,Shadow=0,MarginV=30"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={srt}:force_style='{style}'",
        "-c:a", "copy",         # keep the narration as-is
        output_path,
    ]
    run_ffmpeg(cmd)
    return output_path