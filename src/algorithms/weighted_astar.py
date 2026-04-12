"""Weighted A* — f(n) = g(n) + w * h(n). w > 1 trades optimality for speed."""
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


def find_path(graph, start_id, goal_id, heuristic_fn, params=None) -> PathResult:
    t0 = time.perf_counter()
    params = params or {}
    w = float(params.get("w", 1.5))
    overrides = params.get("manual_overrides_map")

    tiebreak = itertools.count()
    h_start = heuristic_fn(start_id, goal_id, graph, params)
    heap: list[tuple[float, int, str]] = [(w * h_start, next(tiebreak), start_id)]
    g_score: dict[str, float] = {start_id: 0.0}
    prev: dict[str, str | None] = {start_id: None}
    closed: set[str] = set()
    nodes_expanded = 0

    while heap:
        _, _, current = heapq.heappop(heap)
        if current in closed:
            continue
        closed.add(current)
        nodes_expanded += 1

        if current == goal_id:
            path = reconstruct_path(prev, goal_id)
            real_dist = sum_path_distance(graph, path)
            return PathResult(
                algorithm="weighted_astar",
                path_node_ids=path,
                path_coords=coords_for_path(graph, path),
                distance_m=real_dist,
                estimated_time_s=real_dist / DEFAULT_SPEED_MS,
                nodes_expanded=nodes_expanded,
                compute_time_ms=(time.perf_counter() - t0) * 1000,
            )

        g_current = g_score[current]
        for nb in get_neighbors(graph, current):
            nid = nb["node"]
            if nid in closed:
                continue
            tentative = g_current + get_effective_edge_cost(graph, nb["edge_idx"], overrides)
            if tentative < g_score.get(nid, float("inf")):
                g_score[nid] = tentative
                prev[nid] = current
                f = tentative + w * heuristic_fn(nid, goal_id, graph, params)
                heapq.heappush(heap, (f, next(tiebreak), nid))

    return PathResult(
        algorithm="weighted_astar",
        path_node_ids=[],
        path_coords=[],
        distance_m=-1,
        estimated_time_s=-1,
        nodes_expanded=nodes_expanded,
        compute_time_ms=(time.perf_counter() - t0) * 1000,
        error="No path found",
    )
