"""
Bidirectional A* — run A* from start (forward) and goal (backward) simultaneously.

We expand the side with the smallest f-value at each step. When a node is closed
on BOTH sides, we have a candidate meeting point; we keep the minimum g_f + g_b
sum across all such meetings and stop when that sum can't be improved.
"""
from __future__ import annotations

import heapq
import itertools
import time

from src.algorithms.base import (
    DEFAULT_SPEED_MS,
    PathResult,
    coords_for_path,
    sum_path_distance,
)
from src.graph.loader import get_edge_cost, get_effective_edge_cost, get_neighbors


def _reverse_adjacency(graph: dict, node_id: str) -> list[dict]:
    """
    Backward-search neighbours: since the graph's `adjacency` is a forward
    adjacency list (u -> v with edge_idx pointing to edges[u->v]), we need the
    inverse for the goal-rooted search. We return pseudo-neighbours with the
    forward edge's cost as the backward cost — which is correct under symmetric
    edge weights (distance_m is symmetric).

    Because non-oneway ways already emit a reverse edge in builder.py, the
    forward adjacency of v will contain u for bidirectional streets. So we can
    simply reuse get_neighbors(graph, node_id).
    """
    return get_neighbors(graph, node_id)


def find_path(graph, start_id, goal_id, heuristic_fn, params=None) -> PathResult:
    t0 = time.perf_counter()
    params = params or {}
    overrides = params.get("manual_overrides_map")

    if start_id == goal_id:
        return PathResult(
            algorithm="bidirectional_astar",
            path_node_ids=[start_id],
            path_coords=coords_for_path(graph, [start_id]),
            distance_m=0.0,
            estimated_time_s=0.0,
            nodes_expanded=1,
            compute_time_ms=(time.perf_counter() - t0) * 1000,
        )

    tie_f = itertools.count()
    tie_b = itertools.count()

    # forward search — toward goal
    g_f: dict[str, float] = {start_id: 0.0}
    prev_f: dict[str, str | None] = {start_id: None}
    open_f: list[tuple[float, int, str]] = [
        (heuristic_fn(start_id, goal_id, graph, params), next(tie_f), start_id)
    ]
    closed_f: set[str] = set()

    # backward search — toward start
    g_b: dict[str, float] = {goal_id: 0.0}
    prev_b: dict[str, str | None] = {goal_id: None}
    open_b: list[tuple[float, int, str]] = [
        (heuristic_fn(goal_id, start_id, graph, params), next(tie_b), goal_id)
    ]
    closed_b: set[str] = set()

    meeting_node: str | None = None
    best_sum = float("inf")
    nodes_expanded = 0

    while open_f and open_b:
        # Early termination: when the top-of-heap f on either side exceeds the
        # best candidate meeting cost, the best candidate is provably optimal.
        top_f = open_f[0][0]
        top_b = open_b[0][0]
        if meeting_node is not None and (top_f + top_b) >= best_sum:
            break

        # Expand the side with the smaller f
        if top_f <= top_b:
            _, _, current = heapq.heappop(open_f)
            if current in closed_f:
                continue
            closed_f.add(current)
            nodes_expanded += 1

            for nb in get_neighbors(graph, current):
                nid = nb["node"]
                if nid in closed_f:
                    continue
                tentative = g_f[current] + get_effective_edge_cost(graph, nb["edge_idx"], overrides)
                if tentative < g_f.get(nid, float("inf")):
                    g_f[nid] = tentative
                    prev_f[nid] = current
                    f = tentative + heuristic_fn(nid, goal_id, graph, params)
                    heapq.heappush(open_f, (f, next(tie_f), nid))
                    if nid in g_b:
                        total = tentative + g_b[nid]
                        if total < best_sum:
                            best_sum = total
                            meeting_node = nid
        else:
            _, _, current = heapq.heappop(open_b)
            if current in closed_b:
                continue
            closed_b.add(current)
            nodes_expanded += 1

            for nb in _reverse_adjacency(graph, current):
                nid = nb["node"]
                if nid in closed_b:
                    continue
                tentative = g_b[current] + get_effective_edge_cost(graph, nb["edge_idx"], overrides)
                if tentative < g_b.get(nid, float("inf")):
                    g_b[nid] = tentative
                    prev_b[nid] = current
                    f = tentative + heuristic_fn(nid, start_id, graph, params)
                    heapq.heappush(open_b, (f, next(tie_b), nid))
                    if nid in g_f:
                        total = g_f[nid] + tentative
                        if total < best_sum:
                            best_sum = total
                            meeting_node = nid

    if meeting_node is None:
        return PathResult(
            algorithm="bidirectional_astar",
            path_node_ids=[],
            path_coords=[],
            distance_m=-1,
            estimated_time_s=-1,
            nodes_expanded=nodes_expanded,
            compute_time_ms=(time.perf_counter() - t0) * 1000,
            error="No path found",
        )

    # Stitch forward half (start -> meeting) + backward half (meeting -> goal)
    forward_half: list[str] = []
    node: str | None = meeting_node
    while node is not None:
        forward_half.append(node)
        node = prev_f.get(node)
    forward_half.reverse()

    backward_half: list[str] = []
    node = prev_b.get(meeting_node)
    while node is not None:
        backward_half.append(node)
        node = prev_b.get(node)

    path = forward_half + backward_half
    real_dist = sum_path_distance(graph, path)

    return PathResult(
        algorithm="bidirectional_astar",
        path_node_ids=path,
        path_coords=coords_for_path(graph, path),
        distance_m=real_dist,
        estimated_time_s=real_dist / DEFAULT_SPEED_MS,
        nodes_expanded=nodes_expanded,
        compute_time_ms=(time.perf_counter() - t0) * 1000,
    )
