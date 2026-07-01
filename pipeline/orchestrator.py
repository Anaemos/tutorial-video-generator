import os
import shutil
import subprocess
import time
import uuid
import re
from parser.parser import parse_script
from audio.tts import generate_tts
from audio.subtitles import generate_subtitles
from recording.vscode_automation import open_vscode, type_code, execute_code_in_terminal
from recording.screen_recorder import record_screen, stop_recording
from assembly.merge_video import merge_audio_video
from assembly.subtitle_overlay import add_subtitles
from explainer.scene_parser import parse_explainer_scenes
from explainer.layout import layout_scene
from explainer.excalidraw_builder import write_excalidraw_file
from explainer.recorder import record_excalidraw
from explainer.narration import generate_explainer_narration
from explainer.subtitle_writer import write_explainer_srt


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


def _slugify_filename(text: str, max_len: int = 32) -> str:
    """Make a short, filesystem-safe filename fragment."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].strip("-")


def _build_runnable_code(script) -> str:
    """Combine all tutorial step code blocks into one runnable file."""
    parts: list[str] = []
    for step in script.steps:
        code = step.code.strip("\n")
        if code:
            parts.append(code)
    return "\n\n".join(parts) + "\n"


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


def _compute_pause_beats(n_elements: int, audio_duration_s: float) -> list[int]:
    """
    Return a list of pause durations (ms) to insert mid-animation.

    Strategy: insert multiple pause points to slow down the drawing
    and allow the viewer to absorb the material alongside the audio explanation.
    """
    if n_elements < 3 or audio_duration_s < 3.0:
        return []

    # Generous hold duration (minimum 2.5 seconds, up to 7.5 seconds for longer audios)
    hold = min(7500, max(2500, int(audio_duration_s * 300)))
    
    # Scale the number of pauses based on the audio length
    if audio_duration_s < 7.0:
        return [hold]
    elif audio_duration_s < 15.0:
        return [hold, hold]
    else:
        return [hold, hold, hold]


def _build_explainer_clip(script_path: str, run_id: str) -> str | None:
    """
    Parse any '## Explainer' blocks from the script, render each one to a
    .excalidraw file + MP4 (with narration audio + burned subtitles),
    concatenate them if there are multiple, and return the path to the
    final explainer MP4 (or None if the script has no explainer blocks).

    This is a pure additive function — it does not touch the VS Code
    recording pipeline in any way.
    """
    scenes = parse_explainer_scenes(script_path)
    if not scenes:
        return None

    exc_dir = f"output/explainer/{run_id}"
    os.makedirs(exc_dir, exist_ok=True)

    clip_paths = []
    for idx, scene in enumerate(scenes, start=1):
        scene_slug = _slugify_filename(scene.narration)
        clip_stem = f"{run_id}_{idx:02d}"
        if scene_slug:
            clip_stem = f"{clip_stem}_{scene_slug}"

        exc_path = f"{exc_dir}/{clip_stem}.excalidraw"
        mp3_path = f"{exc_dir}/{clip_stem}_narration.mp3"
        srt_path = f"{exc_dir}/{clip_stem}.srt"
        mp4_path = f"{exc_dir}/{clip_stem}.mp4"

        # Try to generate the scene dynamically via Ollama first, to get a fresh drawing on every run
        generated_scene = None
        try:
            from explainer.scene_generator import generate_explainer_scene
            topic = scene.narration
            print(f"[explainer] Requesting LLM generated scene for topic: {topic!r}")
            generated_scene = generate_explainer_scene(topic, scene_id=scene.scene_id)
            print(f"[explainer] Successfully generated fresh scene with {len(generated_scene.nodes)} nodes")
        except Exception as exc:
            print(f"[explainer] Could not generate scene dynamically (Ollama might not be running): {exc}")
            print(f"[explainer] Falling back to hand-authored/default scene layout")

        if generated_scene:
            # Keep the high-quality original narration
            generated_scene.narration = scene.narration
            scene = generated_scene

        print(f"[explainer] Rendering scene: {scene.scene_id} "
              f"({len(scene.nodes)} nodes, {len(scene.edges)} edges)")

        # Build and save the Excalidraw scene
        layout = layout_scene(scene)
        n_elements = len(scene.nodes) + len(scene.edges)
        write_excalidraw_file(layout, exc_path, narration=scene.narration)

        # Generate narration audio and get its duration
        audio_duration = 0.0
        if scene.narration.strip():
            try:
                audio_duration = generate_explainer_narration(
                    scene.narration, mp3_path
                )
            except Exception as exc:
                print(f"[explainer] WARNING: TTS failed for {scene.scene_id}: {exc}")
                mp3_path = None  # proceed without audio

        # Write .srt subtitle file (proportional split, no Whisper needed)
        if audio_duration > 0 and scene.narration.strip():
            try:
                write_explainer_srt(scene.narration, audio_duration, srt_path)
            except Exception as exc:
                print(f"[explainer] WARNING: subtitle generation failed: {exc}")
                srt_path = None
        else:
            srt_path = None

        # Compute mid-animation pause beats
        pause_beats = _compute_pause_beats(n_elements, audio_duration)
        if getattr(scene, "extra_pause_ms", None):
            pause_beats.extend(int(ms) for ms in scene.extra_pause_ms if int(ms) > 0)
        if pause_beats:
            print(
                f"[explainer] Pause beats: "
                + ", ".join(f"{ms}ms" for ms in pause_beats)
            )

        # Record the animation (with audio mix + subtitle burn)
        record_excalidraw(
            exc_path,
            mp4_path,
            min_duration_s=audio_duration,
            narration_mp3=mp3_path if audio_duration > 0 else None,
            subtitles_srt=srt_path,
            pause_beats=pause_beats if pause_beats else None,
        )
        clip_paths.append(mp4_path)

    final_explainer_path = f"output/explainer/explainer_{run_id}.mp4"
    if len(clip_paths) == 1:
        shutil.copy(clip_paths[0], final_explainer_path)
    else:
        # Concatenate multiple explainer clips with ffmpeg
        concat_list = f"{exc_dir}/concat.txt"
        with open(concat_list, "w") as f:
            for p in clip_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")

        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_list, "-c", "copy", final_explainer_path],
            check=True, capture_output=True,
        )
    return final_explainer_path


def _ensure_has_audio(file_path: str, temp_dir: str) -> str:
    """Check if file has an audio stream. If not, generate a copy with silent audio."""
    import json
    from pathlib import Path
    
    has_audio = False
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_streams",
                "-select_streams", "a",
                "-print_format", "json",
                file_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        info = json.loads(result.stdout)
        has_audio = len(info.get("streams", [])) > 0
    except Exception:
        pass
        
    if has_audio:
        return file_path
        
    file_path_obj = Path(file_path)
    output_path = Path(temp_dir) / f"{file_path_obj.stem}_with_silence.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]
    print(f"[orchestrator] Adding silent audio track to {file_path_obj.name}...")
    subprocess.run(cmd, check=True, capture_output=True)
    return str(output_path)


def _prepend_explainer(explainer_mp4: str, tutorial_mp4: str, out_path: str) -> str:
    """
    Concatenate explainer_mp4 + tutorial_mp4 into out_path using ffmpeg's
    concat filter. This re-encodes the streams, guaranteeing perfect
    audio, video, and subtitle synchronization, and avoiding any codec/format mismatch issues.
    """
    temp_dir = os.path.dirname(out_path)
    
    # Ensure both files have audio streams so that the concat filter doesn't fail
    exp_with_audio = _ensure_has_audio(explainer_mp4, temp_dir)
    tut_with_audio = _ensure_has_audio(tutorial_mp4, temp_dir)
    
    print(f"[orchestrator] Merging videos with concat filter...")
    cmd = [
        "ffmpeg", "-y",
        "-i", exp_with_audio,
        "-i", tut_with_audio,
        "-filter_complex", (
            "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];"
            "[1:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];"
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,aresample=44100,asetpts=PTS-STARTPTS[a0];"
            "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,aresample=44100,asetpts=PTS-STARTPTS[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
        ),
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        out_path,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "ffmpeg failed while prepending explainer clip:\n"
            f"command: {' '.join(cmd)}\n"
            f"stderr:\n{exc.stderr}"
        ) from exc
    
    # Clean up temp files if generated
    if exp_with_audio != explainer_mp4 and os.path.exists(exp_with_audio):
        try:
            os.remove(exp_with_audio)
        except OSError:
            pass
    if tut_with_audio != tutorial_mp4 and os.path.exists(tut_with_audio):
        try:
            os.remove(tut_with_audio)
        except OSError:
            pass
            
    return out_path


def run_pipeline(script_path: str, code_path: str = "input/calculator.py") -> str:
    # Disable PyAutoGUI fail-safe to prevent background run failures
    # when the mouse cursor is naturally resting at (0, 0) during tool execution.
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
    except ImportError:
        pass

    run_id = str(uuid.uuid4())[:8]

    audio_out = f"output/audio/{run_id}_narration.mp3"
    srt_out = f"output/subtitles/{run_id}_subtitles.srt"
    recording_out = f"output/recordings/{run_id}_screen.mp4"
    merged_out = f"output/recordings/{run_id}_merged.mp4"
    final_out = f"output/final/{run_id}_final.mp4"

    for d in ["output/audio", "output/subtitles", "output/recordings", "output/final"]:
        os.makedirs(d, exist_ok=True)

    # ── Explainer pre-roll (additive, does not affect VS Code path) ──────────
    explainer_clip = _build_explainer_clip(script_path, run_id)
    if explainer_clip:
        print(f"[orchestrator] Explainer clip ready: {explainer_clip}")

    script = parse_script(script_path)
    runnable_code = _build_runnable_code(script)

    code_abs_path = os.path.abspath(code_path)
    os.makedirs(os.path.dirname(code_abs_path), exist_ok=True)
    with open(code_abs_path, "w", encoding="utf-8") as f:
        f.write(runnable_code)

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
        open_vscode(code_abs_path)
        for step, duration in zip(script.steps, step_durations):
            type_code(step.code + "\n")
            # hold on this step's code for the rest of its narration window
            # so typing stays roughly in sync with the audio being spoken
            time.sleep(max(duration - 2.0, 1.0))

        # Show the code actually running in the integrated terminal.
        # If the script looks interactive, feed a small demo sequence so the
        # viewer sees output instead of a hanging prompt.
        sample_inputs = None
        try:
            with open(os.path.abspath(code_path), "r", encoding="utf-8") as f:
                code_text = f.read()
            if "input(" in code_text:
                sample_inputs = ["10 + 5", "20 / 4", "10 / 0", "quit"]
        except OSError:
            pass
        execute_code_in_terminal(code_abs_path, sample_inputs=sample_inputs)
    finally:
        stop_recording(recording)

    merge_audio_video(recording_out, audio_out, merged_out)
    add_subtitles(merged_out, srt_out, final_out)

    # ── Prepend explainer clip if one was produced ────────────────────────────
    if explainer_clip:
        combined_out = final_out.replace("_final.mp4", "_with_explainer.mp4")
        _prepend_explainer(explainer_clip, final_out, combined_out)
        print(f"[orchestrator] Full video (explainer + tutorial): {combined_out}")
        return combined_out

    return final_out

