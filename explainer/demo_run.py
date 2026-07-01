"""
explainer/demo_run.py

Standalone smoke test for the explainer pipeline (parse -> layout -> json).
Does NOT touch the VS Code pipeline, parser/, recording/, or assembly/ at all.

Run from the project root:
    python -m explainer.demo_run
"""

from explainer.models import Edge, ExplainerScene, Node
from explainer.layout import layout_scene
from explainer.excalidraw_builder import write_excalidraw_file
from explainer.scene_parser import parse_explainer_scenes


def demo_inline_scene():
    """Build a scene directly in code (no .md parsing) to verify layout + JSON."""
    scene = ExplainerScene(
        scene_id="demo_functions",
        narration="A function takes inputs, does work, and returns a value.",
        nodes=[
            Node(id="n1", label="a, b", kind="input"),
            Node(id="n2", label="add(a, b)", kind="process"),
            Node(id="n3", label="return a + b", kind="output"),
        ],
        edges=[
            Edge(src="n1", dst="n2", label="inputs"),
            Edge(src="n2", dst="n3", label="returns"),
        ],
    )
    layout = layout_scene(scene)
    out_path = write_excalidraw_file(layout, "output/explainer/demo_functions.excalidraw", narration=scene.narration)
    print(f"Wrote {out_path} -- open it at https://excalidraw.com (File > Open) to inspect.")


def demo_from_markdown(path: str):
    """Parse '## Explainer' blocks from an actual script file."""
    scenes = parse_explainer_scenes(path)
    print(f"Found {len(scenes)} explainer scene(s) in {path}")
    for scene in scenes:
        layout = layout_scene(scene)
        out_path = write_excalidraw_file(
            layout, f"output/explainer/{scene.scene_id}.excalidraw", narration=scene.narration
        )
        print(f"  {scene.scene_id}: {len(scene.nodes)} nodes, {len(scene.edges)} edges -> {out_path}")


def demo_generated_scene(topic: str):
    """Generate a scene from a topic via local Ollama (qwen3.5:9b) and render it."""
    from explainer.scene_generator import generate_explainer_scene

    scene = generate_explainer_scene(topic, scene_id="generated_demo")
    print(f"Generated scene: {len(scene.nodes)} nodes, {len(scene.edges)} edges")
    print(f"  narration: {scene.narration}")
    layout = layout_scene(scene)
    out_path = write_excalidraw_file(layout, "output/explainer/generated_demo.excalidraw", narration=scene.narration)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    import os
    import sys

    os.makedirs("output/explainer", exist_ok=True)

    if len(sys.argv) > 1:
        # python -m explainer.demo_run "what is a for loop"
        demo_generated_scene(" ".join(sys.argv[1:]))
    else:
        demo_inline_scene()
