import sys
from pipeline.orchestrator import run_pipeline

if __name__ == "__main__":
    # Enforce Python 3.11 for all team members to guarantee library compatibility
    if sys.version_info.major != 3 or sys.version_info.minor != 11:
        print(f"Error: This project requires Python 3.11 (detected Python {sys.version_info.major}.{sys.version_info.minor}).", file=sys.stderr)
        print("Please set up your virtual environment using Python 3.11 to prevent library dependency failures.", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("usage: python main.py input/sample_tutorial.md")
        sys.exit(1)

    script_path = sys.argv[1]
    output = run_pipeline(script_path)
    print(f"done: {output}")
