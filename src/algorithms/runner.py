"""
Runs all 8 algorithms in parallel and returns a unified comparison result.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from dataclasses import asdict

logging.basicConfig(level=logging.INFO, format="[Runner] %(message)s")
log = logging.getLogger("runner")

ALGO_TIMEOUT_S = 10  # max seconds per algorithm before it's killed

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

    log.info("START  %s → %s  (graph: %d nodes, %d edges)",
             start_id, goal_id, len(graph["nodes"]), len(graph["edges"]))

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
            t_algo = time.perf_counter()
            try:
                result = future.result(timeout=ALGO_TIMEOUT_S)
                elapsed = (time.perf_counter() - t_algo) * 1000
                log.info("  %-22s  OK   %.1f ms  dist=%.0f m  nodes=%d%s",
                         name, elapsed,
                         result.distance_m if result.distance_m > 0 else -1,
                         result.nodes_expanded,
                         f"  ERR={result.error}" if result.error else "")
                results[name] = result
            except FutureTimeoutError:
                elapsed = (time.perf_counter() - t_algo) * 1000
                log.warning("  %-22s  TIMEOUT after %.0f ms", name, elapsed)
                results[name] = PathResult(
                    algorithm=name,
                    path_node_ids=[],
                    path_coords=[],
                    distance_m=-1,
                    estimated_time_s=-1,
                    nodes_expanded=0,
                    compute_time_ms=elapsed,
                    error=f"Timeout after {ALGO_TIMEOUT_S}s",
                )
            except Exception as e:  # noqa: BLE001
                elapsed = (time.perf_counter() - t_algo) * 1000
                log.error("  %-22s  EXCEPTION %.0f ms: %s", name, elapsed, e, exc_info=True)
                results[name] = PathResult(
                    algorithm=name,
                    path_node_ids=[],
                    path_coords=[],
                    distance_m=-1,
                    estimated_time_s=-1,
                    nodes_expanded=0,
                    compute_time_ms=elapsed,
                    error=str(e),
                )

    total_ms = (time.perf_counter() - t_total) * 1000
    log.info("DONE   total=%.1f ms", total_ms)

    # Recalculate estimated_time_s using vehicle-specific speed
    from src.algorithms.base import speed_for_vehicle
    vehicle_speed = speed_for_vehicle(params.get("vehicle_type", "car"))
    for r in results.values():
        if r.distance_m > 0:
            r.estimated_time_s = r.distance_m / vehicle_speed

    # Dijkstra is the optimal ground truth
    optimal_dist = results["dijkstra"].distance_m if "dijkstra" in results else -1
    for r in results.values():
        if r.distance_m > 0 and optimal_dist > 0:
            r.is_optimal = abs(r.distance_m - optimal_dist) < 1.0
            r.optimality_gap_pct = round(
                (r.distance_m - optimal_dist) / optimal_dist * 100, 1
            )

    # Snapped coords = actual graph-node positions (may differ from clicked)
    sn = graph["nodes"][start_id]
    gn = graph["nodes"][goal_id]

    return {
        "start_node": start_id,
        "goal_node": goal_id,
        "start_coords": [start_lat, start_lon],
        "goal_coords": [goal_lat, goal_lon],
        "start_snapped": [sn["lat"], sn["lon"]],
        "goal_snapped": [gn["lat"], gn["lon"]],
        "results": {name: asdict(r) for name, r in results.items()},
        "optimal_distance_m": optimal_dist,
        "total_compute_time_ms": round(total_ms, 1),
    }
