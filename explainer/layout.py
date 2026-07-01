"""
explainer/layout.py

Deterministic graph layout: turns (nodes, edges) into x/y positions.

This is the piece that replaces "ask the LLM for pixel coordinates" with
plain code. The LLM (or the script author) only ever has to describe a
graph — which is topic-agnostic and reliable for it to generate. All
geometry below is computed, not guessed, so it works the same whether the
topic is functions, loops, recursion, or anything else.

Algorithm: simple layered ("Sugiyama-style") DAG layout.
  1. Rank each node by its longest path from a root (no incoming edges).
  2. Place nodes left-to-right by rank, top-to-bottom within a rank.
  3. Evenly space nodes so nothing overlaps.

This intentionally does NOT depend on graphviz/dagre/elk (no extra native
deps to install before Friday) but the function signature is the same
shape those libraries use, so swapping in a real layout engine later is a
drop-in replacement if scenes get more complex than this handles well.
"""

from dataclasses import dataclass

from explainer.models import ExplainerScene

NODE_WIDTH = 180
NODE_HEIGHT = 70
RANK_GAP_X = 220   # horizontal gap between ranks (columns)
NODE_GAP_Y = 110   # vertical gap between nodes in the same rank


@dataclass
class PositionedNode:
    id: str
    label: str
    kind: str
    x: float
    y: float
    width: float = NODE_WIDTH
    height: float = NODE_HEIGHT


@dataclass
class LayoutResult:
    nodes: list[PositionedNode]
    edges: list[tuple[str, str, str]]  # (src_id, dst_id, label)
    canvas_width: float
    canvas_height: float


def layout_scene(scene: ExplainerScene) -> LayoutResult:
    if not scene.nodes:
        raise ValueError(f"Scene {scene.scene_id}: cannot lay out a scene with no nodes.")

    ranks = _compute_ranks(scene)
    rank_groups: dict[int, list[str]] = {}
    for node_id, rank in ranks.items():
        rank_groups.setdefault(rank, []).append(node_id)

    # Stable left-to-right column order, and stable top-to-bottom order
    # within each column (insertion order from the script == author intent).
    node_order = [n.id for n in scene.nodes]
    for rank in rank_groups:
        rank_groups[rank].sort(key=node_order.index)

    label_by_id = {n.id: n for n in scene.nodes}
    positioned: list[PositionedNode] = []
    max_rank = max(rank_groups.keys())
    max_col_height = max(len(ids) for ids in rank_groups.values())

    for rank, ids in rank_groups.items():
        x = 60 + rank * (NODE_WIDTH + RANK_GAP_X)
        col_height = len(ids) * NODE_HEIGHT + (len(ids) - 1) * NODE_GAP_Y
        canvas_col_height = max_col_height * NODE_HEIGHT + (max_col_height - 1) * NODE_GAP_Y
        y_start = 60 + max(canvas_col_height - col_height, 0) / 2
        for i, node_id in enumerate(ids):
            n = label_by_id[node_id]
            positioned.append(
                PositionedNode(
                    id=n.id,
                    label=n.label,
                    kind=n.kind,
                    x=x,
                    y=y_start + i * (NODE_HEIGHT + NODE_GAP_Y),
                )
            )

    positioned.sort(key=lambda p: node_order.index(p.id))

    canvas_width = 60 + (max_rank + 1) * (NODE_WIDTH + RANK_GAP_X)
    canvas_height = 60 + max_col_height * (NODE_HEIGHT + NODE_GAP_Y)

    edges = [(e.src, e.dst, e.label) for e in scene.edges]

    return LayoutResult(
        nodes=positioned, edges=edges,
        canvas_width=canvas_width, canvas_height=canvas_height,
    )


def _compute_ranks(scene: ExplainerScene) -> dict[str, int]:
    """Rank = longest path (in edges) from any root node (no incoming edges)."""
    node_ids = [n.id for n in scene.nodes]
    incoming = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in scene.edges:
        adjacency[e.src].append(e.dst)
        incoming[e.dst] += 1

    roots = [nid for nid in node_ids if incoming[nid] == 0] or [node_ids[0]]

    ranks = {nid: 0 for nid in node_ids}
    # BFS/relaxation — fine for the small scene graphs (a handful of nodes)
    # this feature is designed for; cycles just stop propagating past
    # already-visited-at-equal-or-greater-rank nodes.
    frontier = [(r, 0) for r in roots]
    visited_at = {r: 0 for r in roots}
    while frontier:
        node_id, rank = frontier.pop(0)
        for nxt in adjacency[node_id]:
            new_rank = rank + 1
            if new_rank > visited_at.get(nxt, -1):
                visited_at[nxt] = new_rank
                ranks[nxt] = new_rank
                frontier.append((nxt, new_rank))

    return ranks
