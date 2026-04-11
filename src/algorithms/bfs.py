"""Breadth-First Search — optimizes hop count, not distance."""
from __future__ import annotations

import time
from collections import deque

from src.algorithms.base import (
    DEFAULT_SPEED_MS,
    PathResult,
    coords_for_path,
    reconstruct_path,
    sum_path_distance,
)
from src.graph.loader import get_neighbors


def find_path(graph, start_id, goal_id, heuristic_fn=None, params=None) -> PathResult:
    t0 = time.perf_counter()
    if start_id == goal_id:
        return PathResult(
            algorithm="bfs",
            path_node_ids=[start_id],
            path_coords=coords_for_path(graph, [start_id]),
            distance_m=0.0,
            estimated_time_s=0.0,
            nodes_expanded=1,
            compute_time_ms=(time.perf_counter() - t0) * 1000,
        )

    prev: dict[str, str | None] = {start_id: None}
    queue: deque[str] = deque([start_id])
    nodes_expanded = 0

    while queue:
        current = queue.popleft()
        nodes_expanded += 1

        if current == goal_id:
            path = reconstruct_path(prev, goal_id)
            dist = sum_path_distance(graph, path)
            return PathResult(
                algorithm="bfs",
                path_node_ids=path,
                path_coords=coords_for_path(graph, path),
                distance_m=dist,
                estimated_time_s=dist / DEFAULT_SPEED_MS,
                nodes_expanded=nodes_expanded,
                compute_time_ms=(time.perf_counter() - t0) * 1000,
            )

        for nb in get_neighbors(graph, current):
            nid = nb["node"]
            if nid not in prev:
                prev[nid] = current
                queue.append(nid)

    return PathResult(
        algorithm="bfs",
        path_node_ids=[],
        path_coords=[],
        distance_m=-1,
        estimated_time_s=-1,
        nodes_expanded=nodes_expanded,
        compute_time_ms=(time.perf_counter() - t0) * 1000,
        error="No path found",
    )
