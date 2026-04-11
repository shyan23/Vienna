"""Shared dataclasses and types for all search algorithms."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PathResult:
    algorithm: str
    path_node_ids: list[str]
    path_coords: list[tuple[float, float]]  # [(lat, lon), ...]
    distance_m: float
    estimated_time_s: float
    nodes_expanded: int
    compute_time_ms: float
    is_optimal: Optional[bool] = None
    optimality_gap_pct: Optional[float] = None
    error: Optional[str] = None


def reconstruct_path(prev: dict[str, Optional[str]], goal: str) -> list[str]:
    """Walk `prev` backwards from `goal` to the root, returning nodes in forward order."""
    path: list[str] = []
    node: Optional[str] = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    path.reverse()
    return path


def coords_for_path(graph: dict, path: list[str]) -> list[tuple[float, float]]:
    return [(graph["nodes"][n]["lat"], graph["nodes"][n]["lon"]) for n in path]


def sum_path_distance(graph: dict, path: list[str]) -> float:
    """Sum the edge distances along a node path. Returns 0 if path is empty."""
    if len(path) < 2:
        return 0.0
    adjacency = graph["adjacency"]
    edges = graph["edges"]
    total = 0.0
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        best = None
        for nb in adjacency.get(a, []):
            if nb["node"] == b:
                d = edges[nb["edge_idx"]]["distance_m"]
                if best is None or d < best:
                    best = d
        if best is not None:
            total += best
    return total


# Default vehicle speed for BFS/DFS/etc. (m/s) — ~30 km/h
DEFAULT_SPEED_MS = 8.33
