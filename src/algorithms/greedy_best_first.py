"""Greedy Best-First Search — always expand the node closest to goal by h(n)."""
from __future__ import annotations

import heapq
import itertools
import time

from src.algorithms.base import (
    DEFAULT_SPEED_MS,
    PathResult,
    coords_for_path,
    reconstruct_path,
    sum_path_distance,
)
from src.graph.loader import get_neighbors


def find_path(graph, start_id, goal_id, heuristic_fn, params=None) -> PathResult:
    t0 = time.perf_counter()
    params = params or {}

    tiebreak = itertools.count()
    h0 = heuristic_fn(start_id, goal_id, graph, params)
    heap: list[tuple[float, int, str]] = [(h0, next(tiebreak), start_id)]
    prev: dict[str, str | None] = {start_id: None}
    visited: set[str] = set()
    nodes_expanded = 0

    while heap:
        _, _, current = heapq.heappop(heap)
        if current in visited:
            continue
        visited.add(current)
        nodes_expanded += 1

        if current == goal_id:
            path = reconstruct_path(prev, goal_id)
            dist = sum_path_distance(graph, path)
            return PathResult(
                algorithm="greedy",
                path_node_ids=path,
                path_coords=coords_for_path(graph, path),
                distance_m=dist,
                estimated_time_s=dist / DEFAULT_SPEED_MS,
                nodes_expanded=nodes_expanded,
                compute_time_ms=(time.perf_counter() - t0) * 1000,
            )

        for nb in get_neighbors(graph, current):
            nid = nb["node"]
            if nid in visited or nid in prev:
                continue
            prev[nid] = current
            h = heuristic_fn(nid, goal_id, graph, params)
            heapq.heappush(heap, (h, next(tiebreak), nid))

    return PathResult(
        algorithm="greedy",
        path_node_ids=[],
        path_coords=[],
        distance_m=-1,
        estimated_time_s=-1,
        nodes_expanded=nodes_expanded,
        compute_time_ms=(time.perf_counter() - t0) * 1000,
        error="No path found",
    )
