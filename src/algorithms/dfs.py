"""Depth-First Search with depth limit to bound runtime on cyclic graphs."""
from __future__ import annotations

import time

from src.algorithms.base import (
    DEFAULT_SPEED_MS,
    PathResult,
    coords_for_path,
    sum_path_distance,
)
from src.graph.loader import get_neighbors


def find_path(graph, start_id, goal_id, heuristic_fn=None, params=None) -> PathResult:
    t0 = time.perf_counter()
    max_depth = min(500, len(graph["nodes"]) * 2)

    stack: list[tuple[str, list[str]]] = [(start_id, [start_id])]
    visited = {start_id}
    nodes_expanded = 0

    while stack:
        current, path = stack.pop()
        nodes_expanded += 1

        if current == goal_id:
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

        if len(path) >= max_depth:
            continue

        for nb in get_neighbors(graph, current):
            nid = nb["node"]
            if nid not in visited:
                visited.add(nid)
                stack.append((nid, path + [nid]))

    return PathResult(
        algorithm="dfs",
        path_node_ids=[],
        path_coords=[],
        distance_m=-1,
        estimated_time_s=-1,
        nodes_expanded=nodes_expanded,
        compute_time_ms=(time.perf_counter() - t0) * 1000,
        error="No path found",
    )
