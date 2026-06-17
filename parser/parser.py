"""
parser/parser.py

Parses a structured Markdown tutorial script into a ParsedScript object.

Script format expected:
    # Title

    ## Step N
    narration: "Spoken text."
    code: |
      python_code_here()

Usage:
    from parser.parser import parse_script
    script = parse_script("input/calculator_script.md")
"""

import re
import textwrap
from pathlib import Path

# Import shared data models — do not redefine these here
from parser.models import ParsedScript, TutorialStep


def parse_script(filepath: str) -> ParsedScript:
    """
    Parse a Markdown tutorial script file into a ParsedScript object.

    Args:
        filepath: Path to the .md script file.

    Returns:
        ParsedScript with title and list of TutorialStep objects.

    Raises:
        FileNotFoundError: If the script file does not exist.
        ValueError: If a step is missing narration or code, or the title is absent.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Script file not found: {filepath}")

    raw = path.read_text(encoding="utf-8")
    return _parse_text(raw)


def _parse_text(raw: str) -> ParsedScript:
    """
    Core parsing logic, separated so it can be tested without touching the filesystem.

    Args:
        raw: Full text content of the markdown script.

    Returns:
        ParsedScript instance.
    """
    lines = raw.splitlines()

    title = _extract_title(lines)
    step_blocks = _split_into_step_blocks(lines)

    steps = []
    for i, block in enumerate(step_blocks, start=1):
        step = _parse_step_block(block, step_number=i)
        steps.append(step)

    if not steps:
        raise ValueError("No steps found in script. At least one '## Step N' section is required.")

    return ParsedScript(title=title, steps=steps)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_title(lines: list[str]) -> str:
    """Return the text of the first H1 heading (# Title)."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            if title:
                return title
    raise ValueError("Script must start with a top-level heading: '# Title'")


def _split_into_step_blocks(lines: list[str]) -> list[list[str]]:
    """
    Split the full line list into per-step blocks.
    Each block starts at a '## Step N' heading and runs until the next one.
    """
    blocks: list[list[str]] = []
    current: list[str] | None = None

    for line in lines:
        if re.match(r"^## Step\s+\d+", line.strip()):
            if current is not None:
                blocks.append(current)
            current = [line]
        elif current is not None:
            current.append(line)

    if current is not None:
        blocks.append(current)

    return blocks


def _parse_step_block(block: list[str], step_number: int) -> TutorialStep:
    """
    Parse a single step block (list of lines starting with '## Step N').

    Handles:
    - narration: "quoted string"
    - code: |
        indented block

    Args:
        block: Lines belonging to this step.
        step_number: 1-based index used in error messages.

    Returns:
        TutorialStep with narration and code populated.
    """
    text = "\n".join(block)

    narration = _extract_narration(text, step_number)
    code = _extract_code(text, step_number)

    return TutorialStep(narration=narration, code=code)


def _extract_narration(text: str, step_number: int) -> str:
    """
    Extract the narration value from a step block.

    Matches:   narration: "Some text here."
    """
    # Match narration: "..." allowing for escaped quotes inside
    match = re.search(r'^narration:\s*"((?:[^"\\]|\\.)*)"', text, re.MULTILINE)
    if not match:
        raise ValueError(
            f"Step {step_number}: Missing or malformed 'narration' field. "
            f"Expected format:  narration: \"Your text here.\""
        )
    return match.group(1).strip()


def _extract_code(text: str, step_number: int) -> str:
    """
    Extract the code block from a step block.

    Matches the YAML block scalar pattern:
        code: |
          indented python code
          more code
    """
    # Find 'code: |' then capture every following indented line
    match = re.search(r'^code:\s*\|\s*\n((?:[ \t]+.*\n?)*)', text, re.MULTILINE)
    if not match:
        raise ValueError(
            f"Step {step_number}: Missing or malformed 'code' field. "
            f"Expected format:\n  code: |\n    your_code_here()"
        )

    raw_code = match.group(1)

    # Dedent: remove the common leading whitespace so code aligns to column 0
    dedented = textwrap.dedent(raw_code)

    # Strip trailing blank lines but preserve internal structure
    return dedented.strip()