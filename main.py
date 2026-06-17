import sys
from pipeline.orchestrator import run_pipeline

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python main.py input/sample_tutorial.md")
        sys.exit(1)

    script_path = sys.argv[1]
    output = run_pipeline(script_path)
    print(f"done: {output}")
