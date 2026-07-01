"""
explainer/recorder.py

Records the explainer animation as an MP4 **with narration audio and
burned-in subtitles**.

Pipeline:
  1. Spin up a local HTTP server (serves animator.html + the .excalidraw file)
  2. Launch a headless Chromium via Playwright with video recording enabled
  3. Navigate to the local server with ?pauses=<beat_ms,...> to insert
     mid-animation holds so the viewer can absorb each diagram stage
  4. Wait for window.__animationDone, then hold on the final frame until
     the total narration duration is covered
  5. Close the context → Playwright finalises the .webm recording
  6. Convert .webm → silent MP4 via ffmpeg
  7. Mix narration audio into the silent MP4 (-c:v copy, -c:a aac)
  8. Burn subtitle overlay onto the audio+video MP4 (ffmpeg subtitles filter)

Zero changes to parser/, recording/, assembly/, or pipeline/.
The output is a self-contained MP4 (video + audio + baked subtitles)
that the orchestrator concatenates before the VS Code recording.

Usage (standalone test):
    python -m explainer.recorder scene.excalidraw out.mp4 [narration.mp3] [subs.srt]
"""

import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path


# ── Timing constants (must match animator.html) ───────────────────────────────
_MS_PER_SHAPE  = 450
_MS_PER_TEXT   = 180
_STEP_GAP      = 80
_INITIAL_DELAY = 200
_TAIL_BUFFER   = 800    # ms to hold on final frame after animation ends


def record_excalidraw(
    excalidraw_path: str,
    output_mp4: str,
    min_duration_s: float = 0.0,
    narration_mp3: str | None = None,
    subtitles_srt: str | None = None,
    pause_beats: list[int] | None = None,
) -> str:
    """
    Record the animation for the given .excalidraw scene and save to output_mp4.

    Parameters
    ----------
    excalidraw_path:
        Path to the .excalidraw JSON file.
    output_mp4:
        Destination path for the finished MP4.
    min_duration_s:
        Minimum video length in seconds. Pass the TTS narration duration here
        so the visual holds on the last frame until the audio has finished.
    narration_mp3:
        Optional path to a narration audio file (MP3/WAV). When provided it is
        mixed into the output MP4 (-c:v copy so no re-encode of the video).
    subtitles_srt:
        Optional path to a .srt subtitle file. When provided subtitles are
        burned (hardcoded) into the video using ffmpeg's subtitles filter.
    pause_beats:
        Optional list of hold durations in milliseconds to inject between
        animation steps. Passed to animator.html via ?pauses=ms1,ms2,... so
        the drawing pauses mid-way to let the viewer absorb each stage.
        Leave as None to use the default continuous animation.

    Returns
    -------
    str
        Absolute path to the written MP4.
    """
    exc_path = Path(excalidraw_path).resolve()
    if not exc_path.exists():
        raise FileNotFoundError(f"Scene file not found: {exc_path}")

    out_path = Path(output_mp4).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Estimate animation duration from element count
    scene_data = json.loads(exc_path.read_text(encoding="utf-8"))
    elements   = [e for e in scene_data.get("elements", []) if not e.get("isDeleted")]
    n_shapes   = sum(1 for e in elements if e["type"] in ("rectangle", "arrow"))
    n_texts    = sum(1 for e in elements if e["type"] == "text")
    anim_ms    = (
        _INITIAL_DELAY
        + n_shapes * (_MS_PER_SHAPE + _STEP_GAP)
        + n_texts  * (_MS_PER_TEXT  + _STEP_GAP)
    )

    # Add pause beats to the estimated animation time
    pause_total_ms = sum(pause_beats) if pause_beats else 0

    # Total recording time = max(animation+pauses, narration) + tail buffer
    min_ms            = int(min_duration_s * 1000)
    total_ms          = max(anim_ms + pause_total_ms, min_ms) + _TAIL_BUFFER
    post_anim_hold_ms = max(0, min_ms - (anim_ms + pause_total_ms)) + _TAIL_BUFFER

    print(
        f"[recorder] Animation ~{anim_ms/1000:.1f}s"
        + (f" + {pause_total_ms/1000:.1f}s pauses" if pause_total_ms else "")
        + f" | Narration {min_duration_s:.1f}s"
        + f" | Total recording ~{total_ms/1000:.1f}s"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        html_src = Path(__file__).parent / "animator.html"
        shutil.copy(html_src, tmp / "index.html")
        shutil.copy(exc_path, tmp / "scene.excalidraw")

        port, server, server_thread = _start_server(tmp)

        # Build URL with optional ?pauses= query string
        url = f"http://localhost:{port}/"
        if pause_beats:
            url += "?pauses=" + ",".join(str(ms) for ms in pause_beats)

        try:
            webm_path = _run_playwright(url, tmp, total_ms, post_anim_hold_ms)
        finally:
            server.shutdown()
            server_thread.join(timeout=5)

        # Step 1: webm → silent mp4
        silent_mp4 = tmp / "silent.mp4"
        _webm_to_mp4(webm_path, silent_mp4)

        # Step 2: mix narration audio (if provided)
        if narration_mp3 and Path(narration_mp3).exists():
            with_audio_mp4 = tmp / "with_audio.mp4"
            _mix_audio(silent_mp4, Path(narration_mp3), with_audio_mp4)
        else:
            with_audio_mp4 = silent_mp4

        # Step 3: burn subtitles (if provided)
        if subtitles_srt and Path(subtitles_srt).exists():
            _burn_subtitles(with_audio_mp4, Path(subtitles_srt), out_path)
        else:
            shutil.copy(with_audio_mp4, out_path)

    print(f"[recorder] Saved explainer clip: {out_path}")
    return str(out_path)


# ── HTTP server ───────────────────────────────────────────────────────────────

def _start_server(directory: Path) -> tuple[int, http.server.HTTPServer, threading.Thread]:
    import socket
    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]

    handler = _make_handler(directory)
    server  = http.server.HTTPServer(("localhost", port), handler)
    thread  = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[recorder] Local server -> http://localhost:{port}/")
    return port, server, thread


def _make_handler(directory: Path):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)
        def log_message(self, fmt, *args):
            pass
    return Handler


# ── Playwright recording ──────────────────────────────────────────────────────

def _run_playwright(
    url: str,
    tmp: Path,
    total_timeout_ms: int,
    post_anim_hold_ms: int,
) -> Path:
    from playwright.sync_api import sync_playwright

    video_dir = tmp / "video"
    video_dir.mkdir()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()
        # Forward browser console logs to Python stdout for debugging
        page.on("console", lambda msg: print(f"[browser console] {msg.type}: {msg.text}"))
        page.goto(url, wait_until="networkidle")

        print(f"[recorder] Recording (up to {total_timeout_ms/1000:.1f}s) …")

        # Wait for all strokes (+ pause beats) to finish
        try:
            page.wait_for_function(
                "window.__animationDone === true",
                timeout=total_timeout_ms,
            )
            print(
                f"[recorder] Animation complete — holding "
                f"{post_anim_hold_ms/1000:.1f}s for narration …"
            )
        except Exception:
            print(
                "[recorder] Warning: animationComplete not received — "
                "recording whatever was captured."
            )

        # Hold on the final frame for the remainder of narration time
        page.wait_for_timeout(post_anim_hold_ms)

        video_path_str = page.video.path() if page.video else None
        context.close()
        browser.close()

    if video_path_str and Path(video_path_str).exists():
        return Path(video_path_str)

    webms = list(video_dir.glob("*.webm"))
    if not webms:
        raise RuntimeError(
            "Playwright produced no video. "
            "Run `playwright install chromium` if you haven't already."
        )
    return webms[0]


# ── ffmpeg helpers ────────────────────────────────────────────────────────────

def _webm_to_mp4(webm: Path, mp4: Path) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-i", str(webm),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(mp4),
    ]
    print(f"[recorder] Converting {webm.name} -> {mp4.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")


def _mix_audio(video_mp4: Path, audio: Path, out: Path) -> None:
    """
    Mix narration audio into the video. Video stream is copied (no re-encode).
    Audio is shorter-or-equal to the video; pad with silence if needed.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_mp4),
        "-i", str(audio),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",          # end when the shorter stream ends
        "-map", "0:v:0",
        "-map", "1:a:0",
        str(out),
    ]
    print(f"[recorder] Mixing audio -> {out.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio mix failed:\n{result.stderr}")


def _burn_subtitles(video_mp4: Path, srt: Path, out: Path) -> None:
    """
    Burn subtitle cues from *srt* onto *video_mp4* -> *out*.
    Uses ffmpeg's `subtitles` filter (requires libass).
    The video stream IS re-encoded here (needed for filter_complex).

    The .srt is deleted after a successful burn so that media players
    (e.g. VLC) don't auto-load it as a second external subtitle track
    alongside the already-burned-in cues.
    """
    # Escape the SRT path for the subtitles filter (Windows backslashes -> /)
    srt_escaped = str(srt).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_mp4),
        "-vf", (
            f"subtitles='{srt_escaped}':"
            "force_style='Fontname=Arial,FontSize=22,"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "Outline=2,Shadow=1,Alignment=2,MarginV=30'"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        str(out),
    ]
    print(f"[recorder] Burning subtitles -> {out.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Subtitles filter may be unavailable on some ffmpeg builds;
        # fall back to copying the video without subtitles.
        print(
            f"[recorder] WARNING: subtitle burn failed (libass missing?); "
            f"falling back to no-subtitle copy.\n{result.stderr[-300:]}"
        )
        shutil.copy(video_mp4, out)
        return

    # Delete the sidecar .srt so VLC / other players don't auto-load it
    # as a second subtitle track on top of the already-burned-in cues.
    try:
        srt.unlink()
        print(f"[recorder] Removed sidecar .srt (subtitles burned in)")
    except OSError:
        pass  # non-fatal if deletion fails



# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print(
            "Usage: python -m explainer.recorder "
            "<scene.excalidraw> <output.mp4> "
            "[narration.mp3] [subtitles.srt]"
        )
        sys.exit(1)
    record_excalidraw(
        sys.argv[1],
        sys.argv[2],
        narration_mp3=sys.argv[3] if len(sys.argv) > 3 else None,
        subtitles_srt=sys.argv[4] if len(sys.argv) > 4 else None,
    )
