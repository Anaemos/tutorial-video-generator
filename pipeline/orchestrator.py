import os
import time
import uuid
import re
from parser.parser import parse_script
from audio.tts import generate_tts
from audio.subtitles import generate_subtitles
from recording.vscode_automation import open_vscode, type_code
from recording.screen_recorder import record_screen, stop_recording
from assembly.merge_video import merge_audio_video
from assembly.subtitle_overlay import add_subtitles


def _parse_srt_segments(srt_path: str) -> list[dict]:
    """Parse an SRT file into a list of {start, end, duration, text} dicts.

    Lives here (not in audio/) because audio/ is Person 2's module and
    Rule 1 reserves cross-module logic for the orchestrator only.
    """
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    segments = []
    for block in content.strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        start_str, end_str = lines[1].split(" --> ")
        start = _timestamp_to_seconds(start_str)
        end = _timestamp_to_seconds(end_str)
        segments.append({
            "start": start,
            "end": end,
            "duration": end - start,
            "text": " ".join(lines[2:]).strip(),
        })
    return segments


def _timestamp_to_seconds(ts: str) -> float:
    ts = ts.strip().replace(",", ".")
    h, m, rest = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", text.lower())


def _get_step_durations(srt_path: str, step_narrations: list[str]) -> list[float]:
    """Match SRT segments back to script steps via word-overlap, so each
    step's on-screen typing time matches how long its narration actually
    takes to speak — instead of typing all steps back-to-back instantly.
    """
    segments = _parse_srt_segments(srt_path)
    num_steps = len(step_narrations)
    if not segments:
        return [20.0] * num_steps

    step_words = [set(_normalise(n).split()) for n in step_narrations]
    durations = [0.0] * num_steps

    for seg in segments:
        seg_words = set(_normalise(seg["text"]).split())
        if not seg_words:
            continue
        best_step, best_score = 0, -1.0
        for i, words in enumerate(step_words):
            if not words:
                continue
            overlap = len(seg_words & words) / len(seg_words)
            if overlap > best_score:
                best_score, best_step = overlap, i
        durations[best_step] += seg["duration"]

    total = sum(durations)
    zero_steps = [i for i, d in enumerate(durations) if d == 0.0]
    if zero_steps and total > 0:
        fallback = total / num_steps
        for i in zero_steps:
            durations[i] = fallback

    return [max(d, 5.0) for d in durations]


def run_pipeline(script_path: str, code_path: str = "input/calculator.py") -> str:
    run_id = str(uuid.uuid4())[:8]

    audio_out = f"output/audio/{run_id}_narration.mp3"
    srt_out = f"output/subtitles/{run_id}_subtitles.srt"
    recording_out = f"output/recordings/{run_id}_screen.mp4"
    merged_out = f"output/recordings/{run_id}_merged.mp4"
    final_out = f"output/final/{run_id}_final.mp4"

    for d in ["output/audio", "output/subtitles", "output/recordings", "output/final"]:
        os.makedirs(d, exist_ok=True)

    script = parse_script(script_path)

    narration_text = " ".join(step.narration for step in script.steps)

    generate_tts(narration_text, audio_out)
    generate_subtitles(audio_out, srt_out)

    step_narrations = [step.narration for step in script.steps]
    step_durations = _get_step_durations(srt_out, step_narrations)
    total_narration = sum(step_durations)

    print(f"Total narration: {total_narration:.1f}s across {len(script.steps)} steps")
    for i, d in enumerate(step_durations, 1):
        print(f"  Step {i}: {d:.1f}s")

    # generous buffer so recording doesn't cut off before typing finishes
    recording_duration = int(total_narration) + 30

    recording = record_screen(recording_out, duration=recording_duration)
    try:
        open_vscode(os.path.abspath(code_path))
        for step, duration in zip(script.steps, step_durations):
            type_code(step.code + "\n")
            # hold on this step's code for the rest of its narration window
            # so typing stays roughly in sync with the audio being spoken
            time.sleep(max(duration - 2.0, 1.0))
    finally:
        stop_recording(recording)

    merge_audio_video(recording_out, audio_out, merged_out)
    add_subtitles(merged_out, srt_out, final_out)

    return final_out

