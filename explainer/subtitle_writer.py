"""
explainer/subtitle_writer.py

Generates a .srt subtitle file for a single explainer scene narration.

Strategy: proportional character-count split — identical to the approach
already used in audio/subtitles.py:generate_subtitles_from_timings().
No Whisper run needed; the narration text and total audio duration are
both known before this function is called.

Nothing in this module touches the VS Code pipeline.

Usage:
    from explainer.subtitle_writer import write_explainer_srt
    srt_path = write_explainer_srt(
        narration="A function takes inputs and returns a value.",
        duration_s=4.5,
        output_srt="output/explainer/scene1.srt",
    )
"""

import re
from pathlib import Path


# Maximum characters per subtitle cue line.
# Keeps lines readable at 1280x720.
_MAX_CHARS_PER_CUE = 60

# Minimum display time for any single cue (seconds).
_MIN_CUE_DURATION = 0.8


def write_explainer_srt(
    narration: str,
    duration_s: float,
    output_srt: str,
) -> str:
    """
    Write a .srt file for the given narration string.

    The narration is first split into sentences, then each sentence is
    further split into cues of at most _MAX_CHARS_PER_CUE characters.
    Display time is proportional to character count.

    Parameters
    ----------
    narration:
        The full narration text for this explainer scene.
    duration_s:
        Total audio duration in seconds (used to set cue end-times).
    output_srt:
        Destination .srt file path (created / overwritten).

    Returns
    -------
    str
        Absolute path to the written .srt file.
    """
    out = Path(output_srt)
    out.parent.mkdir(parents=True, exist_ok=True)

    cues = _build_cues(narration, duration_s)

    with open(out, "w", encoding="utf-8") as f:
        for idx, (start, end, text) in enumerate(cues, 1):
            f.write(f"{idx}\n")
            f.write(f"{_fmt(start)} --> {_fmt(end)}\n")
            f.write(f"{text}\n\n")

    print(
        f"[explainer.subtitle_writer] {len(cues)} cue(s) -> {out.name} "
        f"(duration {duration_s:.2f}s)"
    )
    return str(out.resolve())


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_cues(narration: str, duration_s: float) -> list[tuple[float, float, str]]:
    """Return a list of (start_s, end_s, text) triples."""
    # 1. Split into sentences
    sentences = _split_sentences(narration)
    if not sentences:
        return []

    # 2. Further split long sentences into short chunks
    chunks: list[str] = []
    for sentence in sentences:
        chunks.extend(_wrap(sentence, _MAX_CHARS_PER_CUE))

    total_chars = sum(len(c) for c in chunks) or 1

    # 3. Assign proportional durations
    cues: list[tuple[float, float, str]] = []
    cursor = 0.0
    for i, chunk in enumerate(chunks):
        chunk_dur = max(duration_s * len(chunk) / total_chars, _MIN_CUE_DURATION)
        end = min(cursor + chunk_dur, duration_s)
        # Clamp last cue to exactly duration_s
        if i == len(chunks) - 1:
            end = duration_s
        cues.append((cursor, end, chunk))
        cursor = end

    return cues


def _split_sentences(text: str) -> list[str]:
    """Split on sentence-ending punctuation, preserving each sentence."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _wrap(text: str, max_chars: int) -> list[str]:
    """
    Split *text* into lines of at most *max_chars* characters, breaking
    at word boundaries.
    """
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    length = 0

    for word in words:
        if length + len(word) + (1 if current else 0) > max_chars:
            if current:
                lines.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += len(word) + (1 if len(current) > 1 else 0)

    if current:
        lines.append(" ".join(current))

    return lines or [text]


def _fmt(seconds: float) -> str:
    """Format seconds as SRT timestamp HH:MM:SS,mmm."""
    seconds = max(seconds, 0.0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02}:{m:02}:{s:02},{ms:03}"
