from dataclasses import dataclass

@dataclass
class TutorialStep:
    narration: str
    code: str

@dataclass
class ParsedScript:
    title: str
    steps: list[TutorialStep]
