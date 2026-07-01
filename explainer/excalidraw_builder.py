"""
explainer/excalidraw_builder.py

Turns a layout.LayoutResult into a valid .excalidraw scene file (JSON).

This is pure, deterministic serialization — no LLM involved at this stage.
By the time code reaches this module, all coordinates already exist; this
just emits the element schema Excalidraw (and excalidraw-animate) expect:
rectangles, bound text labels, and arrows bound to shape edges.

Output can be opened directly in https://excalidraw.com (File > Open) to
sanity-check a scene by eye, and fed to excalidraw-animate for the
stroke-by-stroke playback that gets screen-recorded.
"""

import json
import math
import random
import string
import time

from explainer.layout import LayoutResult, PositionedNode

# Stroke color per kind — used for both border and text
KIND_STROKE = {
    "process":  "#1e1e1e",
    "input":    "#1971c2",
    "output":   "#2f9e44",
    "decision": "#e8590c",
    "note":     "#868e96",
}

# Subtle background fill per kind — light tint so text stays readable
KIND_FILL = {
    "process":  "#f8f9fa",
    "input":    "#dbe4ff",   # light indigo
    "output":   "#d3f9d8",   # light green
    "decision": "#ffe8cc",   # light orange
    "note":     "#f1f3f5",   # light grey
}

ARROW_COLOR  = "#495057"
LABEL_COLOR  = "#495057"
TITLE_COLOR  = "#868e96"

BASE_FONT_SIZE  = 18       # px, used for short labels
MIN_FONT_SIZE   = 13       # px, floor for long labels
BASE_LABEL_CHARS = 12      # chars at which we start shrinking font
EDGE_LABEL_FONT = 13


def _new_id() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


def _seed() -> int:
    return random.randint(1, 2 ** 31)


def _font_size_for_label(label: str) -> int:
    """Scale font down gracefully for longer labels so they fit in the box."""
    excess = max(0, len(label) - BASE_LABEL_CHARS)
    size = BASE_FONT_SIZE - excess
    return max(size, MIN_FONT_SIZE)


def _base_element(el_type: str, x: float, y: float, width: float, height: float, **extra) -> dict:
    el = {
        "id": _new_id(),
        "type": el_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,        # 1 = Excalidraw's hand-drawn look
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": _seed(),
        "version": 1,
        "versionNonce": _seed(),
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
    }
    el.update(extra)
    return el


def _rect_for_node(node: PositionedNode) -> dict:
    stroke = KIND_STROKE.get(node.kind, "#1e1e1e")
    fill   = KIND_FILL.get(node.kind, "#f8f9fa")
    return _base_element(
        "rectangle", node.x, node.y, node.width, node.height,
        strokeColor=stroke,
        backgroundColor=fill,
        fillStyle="solid",
        strokeWidth=2,
    )


def _bound_text_for_node(node: PositionedNode, rect_id: str) -> dict:
    stroke = KIND_STROKE.get(node.kind, "#1e1e1e")
    font_size = _font_size_for_label(node.label)
    return _base_element(
        "text",
        node.x + 8,
        node.y + node.height / 2 - font_size / 2,
        node.width - 16,
        float(font_size),
        strokeColor=stroke,
        text=node.label,
        fontSize=font_size,
        fontFamily=1,          # 1 = Excalidraw hand-drawn ("Virgil") font
        textAlign="center",
        verticalAlign="middle",
        containerId=rect_id,
        originalText=node.label,
        lineHeight=1.25,
    )


def _arrow(src_rect: dict, dst_rect: dict, label: str) -> tuple[dict, dict | None]:
    # Arrow starts at right-center of source, ends at left-center of dest
    sx = src_rect["x"] + src_rect["width"]
    sy = src_rect["y"] + src_rect["height"] / 2
    dx = dst_rect["x"]
    dy = dst_rect["y"] + dst_rect["height"] / 2

    arrow = _base_element(
        "arrow", sx, sy, dx - sx, dy - sy,
        points=[[0, 0], [dx - sx, dy - sy]],
        strokeColor=ARROW_COLOR,
        strokeWidth=2,
        startBinding={"elementId": src_rect["id"], "focus": 0, "gap": 8},
        endBinding=  {"elementId": dst_rect["id"], "focus": 0, "gap": 8},
        startArrowhead=None,
        endArrowhead="arrow",
        roundness={"type": 2},  # curved arrow shaft
    )

    label_el = None
    if label:
        mid_x = (sx + dx) / 2
        mid_y = (sy + dy) / 2
        label_w = max(len(label) * 8, 60)
        label_el = _base_element(
            "text",
            mid_x - label_w / 2,
            mid_y - 20,          # sit just above the arrow shaft
            float(label_w),
            18.0,
            strokeColor=LABEL_COLOR,
            backgroundColor="#ffffff",
            fillStyle="solid",
            text=label,
            fontSize=EDGE_LABEL_FONT,
            fontFamily=1,
            textAlign="center",
            verticalAlign="middle",
            originalText=label,
            lineHeight=1.25,
        )

    return arrow, label_el


def _title_element(narration: str, canvas_width: float) -> dict:
    """Soft grey narration line across the top of the canvas."""
    max_chars = 90
    display = narration if len(narration) <= max_chars else narration[:max_chars].rstrip() + "…"
    return _base_element(
        "text",
        40, 18,
        canvas_width - 80, 28.0,
        strokeColor=TITLE_COLOR,
        text=display,
        fontSize=15,
        fontFamily=1,
        textAlign="left",
        verticalAlign="middle",
        originalText=display,
        lineHeight=1.25,
    )


def build_excalidraw_scene(layout: LayoutResult, narration: str = "") -> dict:
    """
    Build a full .excalidraw document (dict, JSON-serializable) from a
    LayoutResult.

    Draw order: optional title → rects+text per node → arrows.
    This is the stroke playback order in excalidraw-animate, so the title
    appears first, then nodes build up left-to-right, then connections are
    drawn between them.
    """
    elements = []

    if narration:
        elements.append(_title_element(narration, layout.canvas_width))

    rect_by_id: dict[str, dict] = {}
    for node in layout.nodes:
        rect = _rect_for_node(node)
        text = _bound_text_for_node(node, rect["id"])
        rect["boundElements"] = [{"id": text["id"], "type": "text"}]
        rect_by_id[node.id] = rect
        elements.append(rect)
        elements.append(text)

    for src_id, dst_id, label in layout.edges:
        arrow, label_el = _arrow(rect_by_id[src_id], rect_by_id[dst_id], label)
        elements.append(arrow)
        if label_el:
            elements.append(label_el)

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "tutorial-video-generator/explainer",
        "elements": elements,
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#ffffff",
        },
        "files": {},
    }


def write_excalidraw_file(layout: LayoutResult, out_path: str, narration: str = "") -> str:
    scene = build_excalidraw_scene(layout, narration=narration)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)
    return out_path
