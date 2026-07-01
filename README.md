# Tutorial Video Generator

Generates a full tutorial video from a Markdown script:

- VS Code screen recording
- spoken narration
- captions
- optional explainer pre-roll scenes

The repo is organized as a modular pipeline so each stage can be reviewed and tested independently.

## What It Produces

Running the pipeline creates the final video in `output/final/`.

Typical run output:

- `output/audio/` narration MP3
- `output/subtitles/` SRT captions
- `output/recordings/` screen capture and merged intermediate video
- `output/explainer/` explainer pre-roll clips
- `output/final/` final assembled MP4

Generated files are ignored by git.

## Requirements

- Python 3.11
- `ffmpeg` available on `PATH`
- VS Code installed
- Chromium for Playwright

Optional, for dynamic explainer scene generation:

- local Ollama server
- a pulled model such as `qwen3.5:9b`

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

If you want the dynamic explainer scenes, make sure Ollama is running locally before you start the pipeline.

## Run

```bash
python main.py input/sample_tutorial.md
```

You can also use your own Markdown script:

```bash
python main.py input/calculator_script.md
```

## Script Format

The input file is Markdown with a title, `## Step N` sections, and optional `## Explainer` sections.

### Step blocks

```md
# Tutorial Title

## Step 1
narration: "Text that will be spoken in the video."
code: |
  def add(a, b):
      return a + b
```

### Explainer blocks

Explainer blocks are additive and can be inserted before the step-by-step tutorial. They support:

- `pause_ms: 1500, 1800` to stretch the scene timing
- `narration:` for the explainer voiceover
- `nodes:` and `edges:` for the diagram

Example:

```md
## Explainer
pause_ms: 1500, 1800
narration: "This diagram explains the flow."
nodes:
  - id: n1, label: "Inputs", kind: input
  - id: n2, label: "Process", kind: process
  - id: n3, label: "Output", kind: output
edges:
  - from: n1, to: n2, label: "goes to"
  - from: n2, to: n3, label: "returns"
```

## Pipeline Overview

1. Parse the Markdown script into tutorial steps and explainer scenes.
2. Generate narration audio and subtitles.
3. Render explainer scenes into short MP4 clips.
4. Create `input/calculator.py` from the tutorial code blocks.
5. Record VS Code while the code is typed and then executed in the integrated terminal.
6. Merge the outputs into the final video.

## Repo Layout

- `main.py` - CLI entry point
- `pipeline/orchestrator.py` - coordinates the full run
- `parser/` - Markdown script parsing
- `audio/` - narration and subtitle generation
- `recording/` - VS Code automation and screen capture
- `assembly/` - video merge and subtitle burn-in
- `explainer/` - explainer scene parsing, rendering, narration, and recording
- `input/` - source scripts
- `output/` - generated media
- `tests/` - integration-style checks for the modules

## Testing

```bash
pytest tests/
```

The assembly and recording tests are integration-style, so they depend on local tools like `ffmpeg`, VS Code, and browser automation being available.

## Notes for Review

- The repo is intentionally modular: only `pipeline/orchestrator.py` coordinates across modules.
- Generated artifacts are ignored, so a clean git status should only contain source changes.
- The code targets a reproducible local setup, not a hosted service environment.
