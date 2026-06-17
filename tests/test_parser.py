from parser.parser import parse_script

def test_parse_script():
    result = parse_script("input/sample_tutorial.md")
    assert result is not None
    assert len(result.steps) > 0
