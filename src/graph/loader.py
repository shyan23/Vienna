"""Lazy singleton loader for the Vienna graph JSON."""
from __future__ import annotations

import json
import os
from pathlib import Path

_GRAPH: dict | None = None


def load_graph(path: str | None = None) -> dict:
    """Load the graph JSON once and return the cached instance on subsequent calls."""
    global _GRAPH
    if _GRAPH is None:
        path = path or os.getenv("VIENNA_GRAPH_PATH", "data/vienna_graph.json")
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Graph file not found at {p}. "
                "Run: python scripts/fetch_osm_data.py"
            )
        with open(p) as f:
            _GRAPH = json.load(f)
    return _GRAPH


def reset_graph_cache() -> None:
    global _GRAPH
    _GRAPH = None


def get_node(graph: dict, node_id: str) -> dict:
    return graph["nodes"][node_id]


def get_neighbors(graph: dict, node_id: str) -> list[dict]:
    """Returns list of {node, edge_idx} dicts."""
    return graph["adjacency"].get(node_id, [])


def get_edge(graph: dict, edge_idx: int) -> dict:
    return graph["edges"][edge_idx]


def get_edge_cost(graph: dict, edge_idx: int) -> float:
    """Raw g(n) cost = distance in metres."""
    return graph["edges"][edge_idx]["distance_m"]


def is_edge_blocked(
    graph: dict, edge_idx: int, overrides_map: dict[str, int] | None = None
) -> bool:
    """Return True if the edge is blocked (intensity >= 95)."""
    if not overrides_map:
        return False
    edge = graph["edges"][edge_idx]
    edge_key = f'{edge["from"]}_{edge["to"]}'
    return overrides_map.get(edge_key, 0) >= 95


def get_effective_edge_cost(
    graph: dict,
    edge_idx: int,
    overrides_map: dict[str, int] | None = None,
    params: dict | None = None,
) -> float:
    """Edge cost with manual traffic overrides + road-quality multiplier applied.

    Blocked edges (intensity >= 95) return infinity — impassable.
    Sub-blocked: intensity 0..94 → override multiplier 0.5..2.85.
    Road quality (positive heuristic): primary/secondary arterials get <1,
    rough surfaces / footways get >1, making g(n) time-equivalent.
    """
    edge = graph["edges"][edge_idx]
    base = edge["distance_m"]
    cost = base

    if overrides_map:
        edge_key = f'{edge["from"]}_{edge["to"]}'
        if edge_key in overrides_map:
            intensity = overrides_map[edge_key]
            if intensity >= 95:
                return float("inf")
            cost *= 0.5 + (intensity / 100.0) * 2.5

    if params is not None and params.get("use_road_quality", True):
        from src.heuristics.road_quality import get_road_quality_multiplier
        cost *= get_road_quality_multiplier(edge, params.get("vehicle_type"))

    return cost


# ── Vehicle passability ─────────────────────────────────────────────────
# Which road types each vehicle can traverse.
# metro/train have NO roads in the graph → always impassable.

_MOTOR_ROADS = {
    "residential", "secondary", "tertiary", "primary", "living_street",
    "secondary_link", "unclassified", "busway",
}
_WALK_ROADS = {
    "footway", "residential", "corridor", "steps", "pedestrian",
    "living_street", "path", "platform", "secondary", "tertiary",
    "primary", "secondary_link", "unclassified", "cycleway",
}
_CYCLE_ROADS = {
    "cycleway", "residential", "secondary", "tertiary", "primary",
    "living_street", "secondary_link", "unclassified", "path",
}

# Vehicles with no infrastructure in the road graph
_NO_ROAD_VEHICLES = {"metro", "train"}


def is_edge_passable(graph: dict, edge_idx: int, vehicle: str | None) -> bool:
    """Return True if the given vehicle type can traverse this edge."""
    if not vehicle:
        return True
    if vehicle in _NO_ROAD_VEHICLES:
        return False
    edge = graph["edges"][edge_idx]
    road_type = edge.get("road_type", "")
    if vehicle in ("car", "taxi", "motorcycle", "truck"):
        return road_type in _MOTOR_ROADS
    if vehicle == "bus":
        return edge.get("bus_route", False) or road_type in _MOTOR_ROADS
    if vehicle in ("bicycle", "escooter"):
        return road_type in _CYCLE_ROADS
    if vehicle == "walking":
        return road_type in _WALK_ROADS
    if vehicle == "tram":
        return bool(edge.get("tram_track", False))
    return True  # unknown vehicle → allow all


def nearest_node(graph: dict, lat: float, lon: float, vehicle: str | None = None) -> str:
    """Find the graph node closest to a lat/lon coordinate.

    If `vehicle` is given, prefer the closest node that has at least one
    outgoing edge passable by that vehicle; fall back to absolute nearest
    if none exist (shouldn't happen on a curated graph).
    """
    from src.graph.builder import haversine

    best_id = None
    best_dist = float("inf")
    best_passable_id = None
    best_passable_dist = float("inf")
    for nid, node in graph["nodes"].items():
        d = haversine(lat, lon, node["lat"], node["lon"])
        if d < best_dist:
            best_dist = d
            best_id = nid
        if vehicle and d < best_passable_dist:
            for nb in graph["adjacency"].get(nid, []):
                if is_edge_passable(graph, nb["edge_idx"], vehicle):
                    best_passable_dist = d
                    best_passable_id = nid
                    break
    if best_id is None:
        raise ValueError("Graph has no nodes")
    return best_passable_id or best_id
