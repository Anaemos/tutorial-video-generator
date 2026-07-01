"""
explainer/models.py

Data models for the Explainer (pre-roll concept animation) feature.

This is fully additive — nothing here is imported by parser/models.py or
parser/parser.py, and nothing here changes TutorialStep or ParsedScript.
The VS Code coding-tutorial pipeline does not depend on this module at all.
"""

from dataclasses import dataclass, field


@dataclass
class Node:
    id: str
    label: str
    # kind drives visual styling only (rect color / shape), never layout math.
    # Allowed: "process" | "input" | "output" | "decision" | "note"
    kind: str = "process"


@dataclass
class Edge:
    src: str   # Node.id
    dst: str   # Node.id
    label: str = ""


@dataclass
class ExplainerScene:
    scene_id: str
    narration: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    extra_pause_ms: list[int] = field(default_factory=list)
