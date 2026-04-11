"""
Heuristic factory — stub for Sprint 3.

In Sprint 4/5 this file grows to compose all 22+ heuristics into a single
callable h(node_id, goal_id, graph, params). For the Sprint 3 deliverable
we just expose `make_heuristic(params)` returning a Haversine fallback so
the FastAPI endpoint works end-to-end before any heuristic logic lands.
"""
from __future__ import annotations

from src.graph.builder import haversine

MAX_HEURISTIC_CAP = 50.0


def base_heuristic(node_id: str, goal_id: str, graph: dict, params: dict) -> float:
    node = graph["nodes"][node_id]
    goal = graph["nodes"][goal_id]
    return haversine(node["lat"], node["lon"], goal["lat"], goal["lon"])


def make_heuristic(params: dict):
    """
    Return a closure `h(node_id, goal_id, graph, params)`.

    Sprint 3 baseline — no multipliers yet. Sprint 4/5 will replace this body
    with a composite that walks weather / time / vehicle / Vienna-specific
    heuristics and caches their product per-call.
    """
    def heuristic(node_id: str, goal_id: str, graph: dict, _params: dict) -> float:
        return base_heuristic(node_id, goal_id, graph, params)

    return heuristic
