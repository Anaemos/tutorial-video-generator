"""
tests/test_parser.py

Independent tests for parser/parser.py.
Run with:  pytest tests/test_parser.py -v
"""

import pytest
import textwrap
from parser.parser import _parse_text, parse_script
from parser.models import ParsedScript, TutorialStep


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_SCRIPT = textwrap.dedent("""\
    # My Tutorial

    ## Step 1
    narration: "Hello world narration."
    code: |
      print("hello")
""")

MULTI_STEP_SCRIPT = textwrap.dedent("""\
    # Calculator Tutorial

    ## Step 1
    narration: "First step narration."
    code: |
      def add(a, b):
          return a + b

    ## Step 2
    narration: "Second step narration."
    code: |
      def subtract(a, b):
          return a - b

    ## Step 3
    narration: "Third step narration."
    code: |
      result = add(1, 2)
      print(result)
""")


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestParseTitle:
    def test_extracts_title(self):
        result = _parse_text(MINIMAL_SCRIPT)
        assert result.title == "My Tutorial"

    def test_extracts_title_with_spaces(self):
        script = "# My Padded Title   \n\n## Step 1\nnarration: \"x\"\ncode: |\n  pass\n"
        result = _parse_text(script)
        assert result.title == "My Padded Title"

    def test_calculator_tutorial_title(self):
        result = _parse_text(MULTI_STEP_SCRIPT)
        assert result.title == "Calculator Tutorial"


class TestStepCount:
    def test_single_step(self):
        result = _parse_text(MINIMAL_SCRIPT)
        assert len(result.steps) == 1

    def test_three_steps(self):
        result = _parse_text(MULTI_STEP_SCRIPT)
        assert len(result.steps) == 3


class TestNarration:
    def test_narration_extracted(self):
        result = _parse_text(MINIMAL_SCRIPT)
        assert result.steps[0].narration == "Hello world narration."

    def test_narration_all_steps(self):
        result = _parse_text(MULTI_STEP_SCRIPT)
        assert result.steps[0].narration == "First step narration."
        assert result.steps[1].narration == "Second step narration."
        assert result.steps[2].narration == "Third step narration."

    def test_narration_with_punctuation(self):
        script = "# T\n\n## Step 1\nnarration: \"Hello, world! How are you?\"\ncode: |\n  pass\n"
        result = _parse_text(script)
        assert result.steps[0].narration == "Hello, world! How are you?"


class TestCode:
    def test_code_extracted(self):
        result = _parse_text(MINIMAL_SCRIPT)
        assert 'print("hello")' in result.steps[0].code

    def test_code_dedented(self):
        """Code must be dedented to column 0 regardless of indentation in the file."""
        result = _parse_text(MINIMAL_SCRIPT)
        first_line = result.steps[0].code.splitlines()[0]
        assert not first_line.startswith(" "), "Code should be dedented"

    def test_multiline_code(self):
        result = _parse_text(MULTI_STEP_SCRIPT)
        code = result.steps[0].code
        assert "def add(a, b):" in code
        assert "return a + b" in code

    def test_code_preserves_internal_indentation(self):
        """Internal indentation (e.g. function bodies) must be preserved."""
        result = _parse_text(MULTI_STEP_SCRIPT)
        code = result.steps[0].code
        lines = code.splitlines()
        # 'return a + b' should still be indented relative to 'def add'
        return_line = next(l for l in lines if "return" in l)
        assert return_line.startswith("    "), "Internal indentation must be preserved"


class TestReturnType:
    def test_returns_parsed_script(self):
        result = _parse_text(MINIMAL_SCRIPT)
        assert isinstance(result, ParsedScript)

    def test_steps_are_tutorial_steps(self):
        result = _parse_text(MINIMAL_SCRIPT)
        for step in result.steps:
            assert isinstance(step, TutorialStep)


# ---------------------------------------------------------------------------
# Error / edge-case tests
# ---------------------------------------------------------------------------

class TestErrors:
    def test_missing_title_raises(self):
        script = "## Step 1\nnarration: \"x\"\ncode: |\n  pass\n"
        with pytest.raises(ValueError, match="top-level heading"):
            _parse_text(script)

    def test_missing_narration_raises(self):
        script = "# T\n\n## Step 1\ncode: |\n  pass\n"
        with pytest.raises(ValueError, match="narration"):
            _parse_text(script)

    def test_missing_code_raises(self):
        script = "# T\n\n## Step 1\nnarration: \"hello\"\n"
        with pytest.raises(ValueError, match="code"):
            _parse_text(script)

    def test_no_steps_raises(self):
        script = "# Title\n\nSome intro text with no steps.\n"
        with pytest.raises(ValueError, match="No steps"):
            _parse_text(script)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_script("nonexistent/path/script.md")


class TestFullScript:
    """Parse the actual calculator_script.md and validate structure."""

    def test_parses_calculator_script(self, tmp_path):
        """Write the real script to a temp file and parse it end-to-end."""
        import pathlib
        real_script = pathlib.Path(__file__).parent.parent / "input" / "calculator_script.md"
        if not real_script.exists():
            pytest.skip("calculator_script.md not found — skipping integration test")

        result = parse_script(str(real_script))
        assert result.title == "Calculator Tutorial"
        assert len(result.steps) == 10
        for step in result.steps:
            assert isinstance(step.narration, str) and len(step.narration) > 0
            assert isinstance(step.code, str) and len(step.code) > 0