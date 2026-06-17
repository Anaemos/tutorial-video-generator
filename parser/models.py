"""
parser/models.py

Shared data models for the tutorial video generator pipeline.
Everyone imports from here. Do NOT duplicate these in other modules.
"""

from dataclasses import dataclass


@dataclass
class TutorialStep:
    narration: str
    code: str


@dataclass
class ParsedScript:
    title: str
    steps: list[TutorialStep]