"""Depth-First Search — uses a visited set (not path list) for O(V+E) performance."""
from __future__ import annotations

import time

from src.algorithms.base import (
    DEFAULT_SPEED_MS,
    PathResult,
    coords_for_path,
    reconstruct_path,
    sum_path_distance,
)
from src.graph.loader import get_neighbors, is_edge_blocked


def find_path(graph, start_id, goal_id, heuristic_fn=None, params=None) -> PathResult:
    t0 = time.perf_counter()
    params = params or {}
    overrides = params.get("manual_overrides_map")

    # prev[node] = parent — tracks visited nodes and allows path reconstruction
    prev: dict[str, str | None] = {start_id: None}
    stack: list[str] = [start_id]
    nodes_expanded = 0

    while stack:
        current = stack.pop()
        nodes_expanded += 1

        if current == goal_id:
            path = reconstruct_path(prev, goal_id)
            dist = sum_path_distance(graph, path)
            return PathResult(
                algorithm="dfs",
                path_node_ids=path,
                path_coords=coords_for_path(graph, path),
                distance_m=dist,
                estimated_time_s=dist / DEFAULT_SPEED_MS,
                nodes_expanded=nodes_expanded,
                compute_time_ms=(time.perf_counter() - t0) * 1000,
            )

        for nb in get_neighbors(graph, current):
            nid = nb["node"]
            if nid not in prev and not is_edge_blocked(graph, nb["edge_idx"], overrides):
                prev[nid] = current
                stack.append(nid)

    return PathResult(
        algorithm="dfs",
        path_node_ids=[],
        path_coords=[],
        distance_m=-1,
        estimated_time_s=-1,
        nodes_expanded=nodes_expanded,
        compute_time_ms=(time.perf_counter() - t0) * 1000,
        error=f"No path found (expanded {nodes_expanded} nodes)",
    )
