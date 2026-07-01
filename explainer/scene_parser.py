"""
explainer/scene_parser.py

Parses "## Explainer" blocks out of a tutorial script .md file.

This is a SEPARATE, ADDITIVE parse pass over the same input file used by
parser/parser.py. It does not import from, modify, or call parser/parser.py.
Its block-detection regex (`^## Explainer`) never matches `^## Step` + digits,
so the existing VS Code step parsing is completely unaffected even when
both block types appear in the same script file.

Script format expected (can be interleaved with "## Step N" blocks freely):

    ## Explainer
    pause_ms: 1200, 1500
    narration: "A function takes inputs, does work, and returns a value."
    nodes:
      - id: n1, label: "add(a, b)", kind: process
      - id: n2, label: "a, b", kind: input
      - id: n3, label: "a + b", kind: output
    edges:
      - from: n2, to: n1, label: "inputs"
      - from: n1, to: n3, label: "returns"

Usage:
    from explainer.scene_parser import parse_explainer_scenes
    scenes = parse_explainer_scenes("input/calculator_script.md")
"""

import re
from pathlib import Path

from explainer.models import Edge, ExplainerScene, Node


def parse_explainer_scenes(filepath: str) -> list[ExplainerScene]:
    """
    Parse all "## Explainer" blocks in a script file into ExplainerScene objects.

    Args:
        filepath: Path to the .md script file (same file your VS Code
            parser already reads — blocks are distinguished by heading).

    Returns:
        List of ExplainerScene. Empty list if the script has no explainer
        blocks at all (this is a normal, non-error case — older scripts
        with only "## Step N" blocks keep working unmodified).
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Script file not found: {filepath}")

    raw = path.read_text(encoding="utf-8")
    return _parse_text(raw)


def _parse_text(raw: str) -> list[ExplainerScene]:
    lines = raw.splitlines()
    blocks = _split_into_explainer_blocks(lines)

    scenes = []
    for i, block in enumerate(blocks, start=1):
        scenes.append(_parse_explainer_block(block, scene_number=i))
    return scenes


def _split_into_explainer_blocks(lines: list[str]) -> list[list[str]]:
    """
    Split the full line list into per-explainer blocks.
    Each block starts at a '## Explainer' heading and runs until the next
    '## ' heading of ANY kind (Explainer or Step), so it never swallows
    a following Step block.
    """
    blocks: list[list[str]] = []
    current: list[str] | None = None

    for line in lines:
        stripped = line.strip()
        if re.match(r"^## Explainer\b", stripped):
            if current is not None:
                blocks.append(current)
            current = [line]
        elif stripped.startswith("## ") and current is not None:
            # Hit the next heading (e.g. "## Step 3") — close current block.
            blocks.append(current)
            current = None
        elif current is not None:
            current.append(line)

    if current is not None:
        blocks.append(current)

    return blocks


def _parse_explainer_block(block: list[str], scene_number: int) -> ExplainerScene:
    text = "\n".join(block)

    extra_pause_ms = _extract_pause_ms(text)
    narration = _extract_narration(text, scene_number)
    nodes = _extract_items(text, "nodes", scene_number)
    edges_raw = _extract_items(text, "edges", scene_number)

    node_objs = [
        Node(id=n["id"], label=n["label"], kind=n.get("kind", "process"))
        for n in nodes
    ]
    node_ids = {n.id for n in node_objs}

    edge_objs = []
    for e in edges_raw:
        src, dst = e.get("from"), e.get("to")
        if src not in node_ids or dst not in node_ids:
            raise ValueError(
                f"Explainer block {scene_number}: edge references unknown node "
                f"id(s) (from={src!r}, to={dst!r}). Declared node ids: {sorted(node_ids)}"
            )
        edge_objs.append(Edge(src=src, dst=dst, label=e.get("label", "")))

    return ExplainerScene(
        scene_id=f"explainer_{scene_number}",
        narration=narration,
        nodes=node_objs,
        edges=edge_objs,
        extra_pause_ms=extra_pause_ms,
    )


def _extract_pause_ms(text: str) -> list[int]:
    match = re.search(r'^pause_ms:\s*([0-9,\s]+)\s*$', text, re.MULTILINE)
    if not match:
        return []

    pauses: list[int] = []
    for part in match.group(1).split(","):
        value = part.strip()
        if not value:
            continue
        try:
            pause = int(value)
        except ValueError as exc:
            raise ValueError(f"Invalid pause_ms value: {value!r}") from exc
        if pause > 0:
            pauses.append(pause)

    return pauses


def _extract_narration(text: str, scene_number: int) -> str:
    match = re.search(r'^narration:\s*"((?:[^"\\]|\\.)*)"', text, re.MULTILINE)
    if not match:
        raise ValueError(
            f"Explainer block {scene_number}: missing or malformed 'narration' field. "
            f'Expected format:  narration: "Your text here."'
        )
    return match.group(1).strip()


def _extract_items(text: str, key: str, scene_number: int) -> list[dict]:
    """
    Extract a `key:` list section (e.g. 'nodes:' or 'edges:') made of
    '- field: value, field: "quoted value", ...' lines, and parse each
    line into a dict of field -> value.
    """
    section_match = re.search(
        rf'^{key}:\s*\n((?:[ \t]*-.*\n?)*)', text, re.MULTILINE
    )
    if not section_match:
        if key == "nodes":
            raise ValueError(
                f"Explainer block {scene_number}: missing 'nodes:' section."
            )
        return []  # edges are optional (a single-node scene is valid)

    items = []
    for line in section_match.group(1).splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        body = stripped[1:].strip()
        items.append(_parse_field_list(body, key, scene_number))
    return items


def _parse_field_list(body: str, key: str, scene_number: int) -> dict:
    """
    Parse 'id: n1, label: "add(a, b)", kind: process' into a dict.
    Handles commas inside quoted values correctly.
    """
    fields = {}
    # Matches: word: "quoted, value"  OR  word: bareword
    pattern = re.compile(r'(\w+):\s*(".*?"|[^,]+)')
    for m in pattern.finditer(body):
        field_name, value = m.group(1), m.group(2).strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        fields[field_name] = value

    required = {"nodes": ("id", "label"), "edges": ("from", "to")}[key]
    missing = [f for f in required if f not in fields]
    if missing:
        raise ValueError(
            f"Explainer block {scene_number}: {key} entry missing required "
            f"field(s) {missing}: '{body}'"
        )
    return fields
