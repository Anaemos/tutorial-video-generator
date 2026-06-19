import os
import uuid
from parser.parser import parse_script
from audio.tts import generate_tts
from audio.subtitles import generate_subtitles
from recording.vscode_automation import open_vscode, type_code
from recording.screen_recorder import record_screen, stop_recording
from assembly.merge_video import merge_audio_video
from assembly.subtitle_overlay import add_subtitles

def run_pipeline(script_path: str) -> str:
    run_id = str(uuid.uuid4())[:8]

    audio_out = f"output/audio/{run_id}_narration.mp3"
    srt_out = f"output/subtitles/{run_id}_subtitles.srt"
    recording_out = f"output/recordings/{run_id}_screen.mp4"
    merged_out = f"output/recordings/{run_id}_merged.mp4"
    final_out = f"output/final/{run_id}_final.mp4"

    script = parse_script(script_path)

    narration_text = " ".join(step.narration for step in script.steps)
    code_blocks = [step.code for step in script.steps]

    generate_tts(narration_text, audio_out)
    generate_subtitles(audio_out, srt_out)
    recording = record_screen(recording_out, duration=None)
    try:
        open_vscode(code_path)
        for step in script.steps:
            type_code(step.code + "\n")
    finally:
        stop_recording(recording)
    merge_audio_video(recording_out, audio_out, merged_out)
    add_subtitles(merged_out, srt_out, final_out)

    return final_out
