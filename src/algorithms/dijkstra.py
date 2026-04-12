"""Dijkstra — optimal shortest-path. Used as the ground-truth reference."""
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
from src.graph.loader import get_edge_cost, get_effective_edge_cost, get_neighbors


def find_path(graph, start_id, goal_id, heuristic_fn=None, params=None) -> PathResult:
    t0 = time.perf_counter()
    params = params or {}
    overrides = params.get("manual_overrides_map")

    tiebreak = itertools.count()
    heap: list[tuple[float, int, str]] = [(0.0, next(tiebreak), start_id)]
    dist: dict[str, float] = {start_id: 0.0}
    prev: dict[str, str | None] = {start_id: None}
    visited: set[str] = set()
    nodes_expanded = 0

    while heap:
        g, _, current = heapq.heappop(heap)
        if current in visited:
            continue
        visited.add(current)
        nodes_expanded += 1

        if current == goal_id:
            path = reconstruct_path(prev, goal_id)
            real_dist = sum_path_distance(graph, path)
            return PathResult(
                algorithm="dijkstra",
                path_node_ids=path,
                path_coords=coords_for_path(graph, path),
                distance_m=real_dist,
                estimated_time_s=real_dist / DEFAULT_SPEED_MS,
                nodes_expanded=nodes_expanded,
                compute_time_ms=(time.perf_counter() - t0) * 1000,
            )

        for nb in get_neighbors(graph, current):
            nid = nb["node"]
            if nid in visited:
                continue
            new_dist = g + get_effective_edge_cost(graph, nb["edge_idx"], overrides)
            if new_dist < dist.get(nid, float("inf")):
                dist[nid] = new_dist
                prev[nid] = current
                heapq.heappush(heap, (new_dist, next(tiebreak), nid))

    return PathResult(
        algorithm="dijkstra",
        path_node_ids=[],
        path_coords=[],
        distance_m=-1,
        estimated_time_s=-1,
        nodes_expanded=nodes_expanded,
        compute_time_ms=(time.perf_counter() - t0) * 1000,
        error="No path",
    )
