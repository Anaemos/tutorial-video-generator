"""
explainer/scene_generator.py

Generates an ExplainerScene from a plain-language topic using a local
Ollama model (e.g. qwen3.5:9b). This is additive: nothing else in the
pipeline depends on this module. If generation fails or Ollama isn't
running, the rest of the explainer pipeline (scene_parser.py for
hand-authored "## Explainer" blocks) keeps working unaffected.

Usage:
    from explainer.scene_generator import generate_explainer_scene
    scene = generate_explainer_scene("what is a function, with add(a,b) example")
"""

import json
import re

import requests

from explainer.models import Edge, ExplainerScene, Node

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"

ALLOWED_KINDS = {"process", "input", "output", "decision", "note"}

SYSTEM_PROMPT = """You design simple diagrams to explain a single beginner \
programming concept. Output ONLY a JSON object, no markdown fences, no \
commentary, no explanation -- just the raw JSON.

Schema (follow exactly):
{
  "narration": "one or two spoken sentences explaining the concept",
  "nodes": [
    {"id": "n1", "label": "short text (3-5 words max)", "kind": "input"}
  ],
  "edges": [
    {"from": "n1", "to": "n2", "label": "short label or empty string"}
  ]
}

Hard rules:
- "kind" must be exactly one of: process, input, output, decision, note
- Use 3 to 5 nodes total. Never more than 6.
- Every edge's "from" and "to" must reference a node id that exists in "nodes"
- Node labels must be SHORT (think diagram box text, not sentences)
- The graph should read left-to-right as a simple flow: inputs -> processing -> output
- Do not invent ids that aren't used; do not leave any node disconnected unless there is only one node
- Output raw JSON only. No ```json fences. No prose before or after.
"""


def generate_explainer_scene(topic: str, scene_id: str = "generated_1") -> ExplainerScene:
    """
    Ask the local Ollama model to design a small explainer diagram for
    `topic`, validate its output, and return an ExplainerScene ready for
    explainer.layout.layout_scene().

    Raises:
        RuntimeError: if Ollama is unreachable.
        ValueError: if the model's output fails schema validation after retries.
    """
    raw = _call_ollama(topic)
    data = _extract_json(raw)
    return _validate_and_build(data, scene_id)


def _call_ollama(topic: str, retries: int = 2) -> str:
    prompt = f"{SYSTEM_PROMPT}\n\nConcept to explain: {topic}"
    last_err = None
    
    selected_model = MODEL
    try:
        tags_resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if tags_resp.status_code == 200:
            models_list = tags_resp.json().get("models", [])
            installed_names = [m["name"] for m in models_list]
            if selected_model not in installed_names and selected_model + ":latest" not in installed_names:
                if installed_names:
                    selected_model = installed_names[0]
                    print(f"[scene_generator] Default model {MODEL!r} not found. Falling back to: {selected_model!r}")
    except Exception:
        pass

    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": selected_model,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,   # Qwen3 is a hybrid reasoning model -- disable
                                       # the <think> pass. Faster, and avoids it
                                       # conflicting with strict JSON output below.
                    "options": {"temperature": 0.3},
                },
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json()["response"]
            if not text.strip():
                last_err = RuntimeError("Ollama returned an empty response")
                continue
            return text
        except requests.exceptions.ConnectionError as e:
            last_err = e
            break  # no point retrying if Ollama isn't running at all
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(
        f"Could not get a usable response from Ollama at {OLLAMA_URL} "
        f"(model={selected_model}). Is `ollama serve` running and is the model pulled? "
        f"Underlying error: {last_err}"
    )


def _extract_json(raw: str) -> dict:
    """
    Pull the JSON object out of the model's raw text response. Defensive
    against:
    - a leftover <think>...</think> block, if this Ollama version doesn't
      support the `think: False` request param yet
    - stray ```json fences
    - any prose the model adds before/after the JSON despite instructions
    """
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*|```$", "", text, flags=re.MULTILINE).strip()

    # Find the first balanced {...} block in case there's still leading/
    # trailing prose around it.
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in model output. Raw output:\n{raw}")

    depth = 0
    end = None
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise ValueError(f"Unbalanced JSON in model output. Raw output:\n{raw}")

    candidate = text[start:end]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON. Raw output:\n{raw}") from e


def _validate_and_build(data: dict, scene_id: str) -> ExplainerScene:
    if "narration" not in data or not isinstance(data["narration"], str):
        raise ValueError(f"Missing/invalid 'narration' in model output: {data}")
    if "nodes" not in data or not isinstance(data["nodes"], list) or not data["nodes"]:
        raise ValueError(f"Missing/empty 'nodes' in model output: {data}")
    if len(data["nodes"]) > 6:
        raise ValueError(f"Model returned {len(data['nodes'])} nodes; max is 6 for readability.")

    nodes = []
    node_ids = set()
    for n in data["nodes"]:
        if "id" not in n or "label" not in n:
            raise ValueError(f"Node missing id/label: {n}")
        kind = n.get("kind", "process")
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"Node {n['id']!r} has invalid kind {kind!r}. Allowed: {ALLOWED_KINDS}")
        if n["id"] in node_ids:
            raise ValueError(f"Duplicate node id: {n['id']!r}")
        node_ids.add(n["id"])
        nodes.append(Node(id=n["id"], label=n["label"], kind=kind))

    edges = []
    for e in data.get("edges", []):
        if e.get("from") not in node_ids or e.get("to") not in node_ids:
            raise ValueError(
                f"Edge references unknown node id(s): {e}. Known ids: {sorted(node_ids)}"
            )
        edges.append(Edge(src=e["from"], dst=e["to"], label=e.get("label", "")))

    return ExplainerScene(
        scene_id=scene_id,
        narration=data["narration"].strip(),
        nodes=nodes,
        edges=edges,
    )
