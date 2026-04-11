"""
Runs all 8 algorithms in parallel and returns a unified comparison result.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict

from src.algorithms import (
    astar,
    bfs,
    bidirectional_astar,
    dfs,
    dijkstra,
    greedy_best_first,
    ucs,
    weighted_astar,
)
from src.algorithms.base import PathResult
from src.graph.loader import load_graph, nearest_node

ALGORITHMS = {
    "bfs": bfs,
    "dfs": dfs,
    "ucs": ucs,
    "dijkstra": dijkstra,
    "greedy": greedy_best_first,
    "astar": astar,
    "weighted_astar": weighted_astar,
    "bidirectional_astar": bidirectional_astar,
}


def _default_heuristic(node_id, goal_id, graph, params):
    """Admissible fallback: Haversine straight-line distance."""
    from src.graph.builder import haversine

    n = graph["nodes"][node_id]
    g = graph["nodes"][goal_id]
    return haversine(n["lat"], n["lon"], g["lat"], g["lon"])


def run_all(
    start_lat: float,
    start_lon: float,
    goal_lat: float,
    goal_lon: float,
    params: dict | None = None,
    heuristic_fn=None,
) -> dict:
    """
    Find path for all 8 algorithms between two lat/lon points.
    Returns a unified comparison dict.
    """
    params = params or {}
    if heuristic_fn is None:
        heuristic_fn = _default_heuristic

    graph = load_graph()
    start_id = nearest_node(graph, start_lat, start_lon)
    goal_id = nearest_node(graph, goal_lat, goal_lon)

    t_total = time.perf_counter()
    results: dict[str, PathResult] = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(
                algo.find_path, graph, start_id, goal_id, heuristic_fn, params
            ): name
            for name, algo in ALGORITHMS.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:  # noqa: BLE001
                results[name] = PathResult(
                    algorithm=name,
                    path_node_ids=[],
                    path_coords=[],
                    distance_m=-1,
                    estimated_time_s=-1,
                    nodes_expanded=0,
                    compute_time_ms=0,
                    error=str(e),
                )

    total_ms = (time.perf_counter() - t_total) * 1000

    # Dijkstra is the optimal ground truth
    optimal_dist = results["dijkstra"].distance_m if "dijkstra" in results else -1
    for r in results.values():
        if r.distance_m > 0 and optimal_dist > 0:
            r.is_optimal = abs(r.distance_m - optimal_dist) < 1.0
            r.optimality_gap_pct = round(
                (r.distance_m - optimal_dist) / optimal_dist * 100, 1
            )

    return {
        "start_node": start_id,
        "goal_node": goal_id,
        "start_coords": [start_lat, start_lon],
        "goal_coords": [goal_lat, goal_lon],
        "results": {name: asdict(r) for name, r in results.items()},
        "optimal_distance_m": optimal_dist,
        "total_compute_time_ms": round(total_ms, 1),
    }
