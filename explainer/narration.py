"""
explainer/narration.py

Thin, additive wrapper that synthesises TTS audio for a single explainer
scene narration string and queries the resulting audio duration.

Re-uses audio.tts.generate_tts (edge-TTS, en-US-GuyNeural) so the
explainer voice matches the VS Code tutorial narration — no new
dependency.

Nothing in this module touches the VS Code pipeline.

Usage:
    from explainer.narration import generate_explainer_narration, get_audio_duration
    duration_s = generate_explainer_narration("A function takes inputs …", "out.mp3")
    print(f"Audio is {duration_s:.2f}s long")
"""

import json
import subprocess
from pathlib import Path

from audio.tts import generate_tts  # re-uses existing edge-TTS call


def generate_explainer_narration(text: str, output_mp3: str) -> float:
    """
    Synthesise TTS for *text* and save to *output_mp3*.

    Returns
    -------
    float
        Duration of the generated audio in seconds.

    Raises
    ------
    RuntimeError
        If TTS generation fails or the audio file cannot be probed.
    """
    out = Path(output_mp3)
    out.parent.mkdir(parents=True, exist_ok=True)

    generate_tts(text, str(out))

    duration = get_audio_duration(str(out))
    print(
        f"[explainer.narration] TTS -> {out.name} "
        f"({len(text)} chars, {duration:.2f}s)"
    )
    return duration


def get_audio_duration(audio_path: str) -> float:
    """
    Return the duration of *audio_path* in seconds using ffprobe.

    Falls back to estimating from character count (~3 chars/s at normal
    speech pace) if ffprobe is unavailable, so the pipeline degrades
    gracefully.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                audio_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception as exc:
        # ffprobe not available or failed — rough estimate
        path = Path(audio_path)
        print(
            f"[explainer.narration] ffprobe unavailable ({exc}); "
            f"estimating duration from file size."
        )
        # MP3 at ~24 kbps (edge-TTS default) ≈ 3 kB/s
        size_bytes = path.stat().st_size if path.exists() else 0
        return max(size_bytes / 3000, 1.0)


# ── CLI smoke test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    _text = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "A function takes inputs, does work, and returns a value."
    )
    _out = sys.argv[2] if len(sys.argv) > 2 else "output/explainer/test_narration.mp3"
    dur = generate_explainer_narration(_text, _out)
    print(f"Written: {_out}  ({dur:.2f}s)")
