"""Step 1 of assembly: put the narration audio onto the screen recording."""

from assembly.utils import validate_file_exists, run_ffmpeg


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> str:
    """Replace the screen recording's audio track with the TTS narration.

    The screen recording has no meaningful audio, so this is a straight
    replacement (not a mix). The video stream is copied without re-encoding
    (fast); only the audio is encoded to AAC so it sits cleanly in the MP4.
    Re-encoding of the video happens later, once, in subtitle_overlay.

    Returns the path to the merged video.
    """
    validate_file_exists(video_path)
    validate_file_exists(audio_path)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,       # input 0: video
        "-i", audio_path,       # input 1: narration
        "-map", "0:v:0",        # take video from input 0
        "-map", "1:a:0",        # take audio from input 1
        "-c:v", "copy",         # don't re-encode video (fast)
        "-c:a", "aac",          # encode narration to AAC for MP4
        "-b:a", "192k",
        "-shortest",            # stop at the shorter of the two streams
        output_path,
    ]
    run_ffmpeg(cmd)
    return output_path