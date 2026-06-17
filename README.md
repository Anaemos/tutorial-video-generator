# Tutorial Video Generator

Takes a structured Markdown script as input and produces a complete tutorial video with VS Code
screen recording, TTS narration, and synced captions. One human step: provide the script.

---

## Quick Start

```bash
pip install -r requirements.txt
python main.py input/sample_tutorial.md
```

Output lands in `output/final/{run_id}_final.mp4`

---

## Script Format

Input files are Markdown with this structure:

```md
# Tutorial Title

## Step 1
narration: "Text that will be spoken in the video."
code: |
  def add(a, b):
      return a + b

## Step 2
narration: "Now let's test it."
code: |
  print(add(10, 5))
```

Rules:
- Every step needs both a narration field and a code field
- narration is a quoted string on one line
- code uses block scalar format (pipe character, code indented below)
- Steps are processed in order top to bottom

---

## Pipeline Flow

```
input/script.md
      |
      v
parser/parser.py          parse_script()
      |
      returns ParsedScript object (title + list of TutorialStep)
      |
      v
audio/tts.py              generate_tts()
      |                   -> output/audio/{id}_narration.mp3
      v
audio/subtitles.py        generate_subtitles()
      |                   -> output/subtitles/{id}_subtitles.srt
      |
      |    recording/vscode_automation.py    open_vscode(), type_code()
      |    recording/screen_recorder.py      record_screen()
      |                                      -> output/recordings/{id}_screen.mp4
      |                                      |
      +------------------------------------------+
                         |
                         v
              assembly/merge_video.py        merge_audio_video()
                         |                   -> output/recordings/{id}_merged.mp4
                         v
              assembly/subtitle_overlay.py   add_subtitles()
                         |                   -> output/final/{id}_final.mp4
                         v
                    FINAL.mp4
```

The entire sequence is coordinated by `pipeline/orchestrator.py`.
`main.py` just calls `run_pipeline()` and prints the result.

---

## Folder Structure and File Responsibilities

### main.py

Entry point. Reads the script path from the command line and calls `run_pipeline()`.
Nothing else lives here. If you want to add CLI flags later, this is where they go.

---

### input/

Holds script files. `sample_tutorial.md` is the reference example used for testing.
Everyone should test their module against this file before submitting a PR.

---

### output/

All generated files land here. Subfolders keep different file types separate so debugging
mid-pipeline failures is easier - if `output/audio/` has a file but `output/recordings/` is
empty, you know exactly where it broke.

- `output/audio/` - narration MP3 files from TTS
- `output/subtitles/` - SRT caption files from Whisper
- `output/recordings/` - raw screen recording and merged video (intermediate files)
- `output/final/` - final assembled video, the actual deliverable

All output subfolders contain a `.gitkeep` file. This is an empty file whose only purpose
is to make git track the folder. Git does not track empty folders on its own. Once real
files land here during a run, `.gitkeep` becomes irrelevant but does no harm.

The entire contents of `output/` are gitignored except the `.gitkeep` files. Generated
video and audio files should never be committed to the repo.

---

### parser/

**Who owns this:** Person 1

**`models.py`**
Defines the data structures that flow between all modules:

```python
@dataclass
class TutorialStep:
    narration: str
    code: str

@dataclass
class ParsedScript:
    title: str
    steps: list[TutorialStep]
```

This file is imported by `parser.py` and by `pipeline/orchestrator.py`. It exists as a
separate file so the data contract between modules is explicit and in one place. If the
script format changes, you update `models.py` and everything downstream adjusts.

**`parser.py`**
Contains `parse_script(script_path: str) -> ParsedScript`.
Reads the Markdown file, extracts title, narration text, and code blocks for each step,
and returns a `ParsedScript` object. This is the only file in the repo that touches the
raw input file.

**`__init__.py`**
Empty file. Required by Python to treat this folder as a package so other files can do
`from parser.parser import parse_script`. Every module folder has one for the same reason.

---

### audio/

**Who owns this:** Person 2

**`tts.py`**
Contains `generate_tts(text: str, output_path: str) -> str`.
Takes the full narration text as a string, generates an MP3 using `edge-tts`, saves it to
`output_path`, and returns the path. Uses `edge-tts` over `pyttsx3` because it produces
significantly better voice quality and is still free with no API key.

**`subtitles.py`**
Contains `generate_subtitles(audio_path: str, output_path: str) -> str`.
Takes the generated MP3, runs it through `faster-whisper` to get word-level timestamps,
formats the output as an SRT file, saves it to `output_path`, and returns the path.
Subtitles are generated from the audio rather than the script text directly because
Whisper's timestamps match the actual audio timing, which is what matters for sync.

**`utils.py`**
Placeholder for shared helpers Person 2 needs internally - for example audio duration
calculation, format validation, or file cleanup. Empty until Person 2 needs it.
If it stays empty by Friday, delete it.

**`__init__.py`**
Same as above - makes the folder a Python package.

---

### recording/

**Who owns this:** Person 3

**`vscode_automation.py`**
Contains `open_vscode(filepath: str) -> None` and `type_code(code: str, delay_per_char: float) -> None`.
`open_vscode` launches VS Code via subprocess with a given file open.
`type_code` uses `pyautogui` to type code into the active window at a human-readable pace.
The `delay_per_char` parameter controls typing speed - slower looks more natural in a tutorial.

**`screen_recorder.py`**
Contains `record_screen(output_path: str, duration: int) -> str`.
Uses `ffmpeg` to capture the screen for the given duration and saves it as an MP4.
Returns the output path. This runs alongside `vscode_automation.py` - recording starts,
then code gets typed, then recording stops.

**`utils.py`**
Placeholder for shared helpers - for example waiting for VS Code to finish launching before
typing starts, or checking that the right window is in focus. Empty until Person 3 needs it.

**`__init__.py`**
Makes the folder a Python package.

---

### assembly/

**Who owns this:** Person 4

**`merge_video.py`**
Contains `merge_audio_video(video_path: str, audio_path: str, output_path: str) -> str`.
Uses `ffmpeg` to replace the screen recording's audio track with the TTS narration.
The screen recording has no meaningful audio so this is a straight replacement, not a mix.
Returns path to the merged video.

**`subtitle_overlay.py`**
Contains `add_subtitles(video_path: str, srt_path: str, output_path: str) -> str`.
Uses `ffmpeg` to burn the SRT captions into the merged video as visible text.
Returns path to the final video. This is the last step in the pipeline.

**`utils.py`**
Placeholder for shared ffmpeg helpers - for example checking that ffmpeg is installed,
getting video duration, or validating that input files exist before processing.
Empty until Person 4 needs it.

**`__init__.py`**
Makes the folder a Python package.

---

### pipeline/

**`orchestrator.py`**
Contains `run_pipeline(script_path: str) -> str`.
This is the only file that imports from all other modules. It calls each function in the
correct order, passes outputs from one step as inputs to the next, and returns the path
to the final video. It does not contain any logic itself - just coordination.

When this project is extended to MCP, this file gets replaced by agent orchestration.
Every other file stays exactly as is.

**`__init__.py`**
Makes the folder a Python package.

---

### mcp/

Empty folder with a `.gitkeep`. Exists as a designated place for MCP tool wrappers when
that work begins. The plan is one file per module:

```
mcp/
  tts_tool.py
  subtitle_tool.py
  recorder_tool.py
  assembler_tool.py
```

Each file will wrap the existing module function with an `@mcp.tool` decorator and nothing
else. The core logic does not move - it stays in the module files.

---

### tests/

One test file per module. Each test calls the module's function with real or dummy inputs
and checks that an output file was actually created. Tests are the integration contract -
if your function passes its test, Person 1 can plug it into the pipeline without surprises.

- `test_parser.py` - Person 1 writes and owns this
- `test_audio.py` - Person 2 writes and owns this
- `test_recording.py` - Person 3 writes and owns this
- `test_assembly.py` - Person 4 writes and owns this

Run all tests: `pytest tests/`

---

## Modularity Rules

**Rule 1 - No module imports from another module**

Each module only imports from the standard library or installed packages. It does not
import from `audio/`, `recording/`, or `assembly/`. Only `pipeline/orchestrator.py` is
allowed to import across modules.

```python
# correct - module only uses external libraries
import edge_tts

# wrong - audio module should never touch assembly
from assembly.merge_video import merge_audio_video
```

**Rule 2 - Every function takes simple inputs and returns a file path**

No function should receive a complex object it did not create itself, except for
`ParsedScript` and `TutorialStep` from `parser/models.py`.

```python
# correct
def generate_tts(text: str, output_path: str) -> str:

# wrong - passing objects from another module's internals
def generate_tts(script: SomeOtherModulesObject) -> str:
```

**Rule 3 - Every function is independently callable**

You should be able to call any function in isolation with dummy inputs and get a real
output without running the whole pipeline. This is what makes testing possible and what
makes MCP wrapping straightforward later.

**Rule 4 - Add your dependencies to requirements.txt as you go**

Do not wait until integration day to add your pip packages. If you install something,
add it to `requirements.txt` immediately and commit it to your branch.

---

## Git Workflow

### Branch Structure

```
main                    stable working code only, nobody commits here directly
  |
  ├── module/parser     Person 1
  ├── module/audio      Person 2
  ├── module/recording  Person 3
  └── module/assembly   Person 4
```

### Getting Started (each person, one time)

```bash
git clone YOUR_REPO_URL
cd tutorial-video-generator
git checkout module/your-branch
```

You are now on your branch. Only touch files inside your own module folder.

### Daily Workflow

```bash
# after writing or changing code
git add .
git commit -m "short description of what you did"
git push origin module/your-branch
```

Commit every time something works. Do not save it all for the end of the day.

### Submitting Your Module

When your module is done and your test passes:

1. Go to github.com, open the repo
2. Click Pull Requests -> New Pull Request
3. Set base: `main`, compare: `module/your-branch`
4. Write one or two lines describing what your module does
5. Create Pull Request
6. Person 1 reviews and merges into main

### Integration (Thursday)

After all PRs are merged, Person 1 runs:

```bash
git checkout main
git pull origin main
python main.py input/sample_tutorial.md
```

This is the first time all four modules run together. Expect issues. Fix them together.

### Rules

- Never commit directly to main
- Only touch files inside your own module folder
- If you need a helper that crosses modules, talk to Person 1 - it goes in orchestrator.py
- Add your pip dependencies to requirements.txt as you go

---

## Future MCP Extension

The entire pipeline is designed so converting to MCP requires no changes to module code.
The only addition is a decorator per function:

```python
# current
def generate_tts(text: str, output_path: str) -> str:
    ...

# future MCP - identical function, one line added
@mcp.tool
def generate_tts(text: str, output_path: str) -> str:
    ...
```

When MCP is live, `pipeline/orchestrator.py` gets replaced by agent orchestration.
The agent calls each tool in sequence the same way the orchestrator does today.
Nothing in the module files changes.

---

## Setup

Requirements:
- Python 3.11 (Recommended for library compatibility, especially faster-whisper)
- ffmpeg installed system-wide (`winget install ffmpeg` on Windows)
- VS Code installed

```bash
pip install -r requirements.txt
```
