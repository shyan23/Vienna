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
    graph: dict, edge_idx: int, overrides_map: dict[str, int] | None = None
) -> float:
    """Edge cost with manual traffic overrides applied.

    Blocked edges (intensity >= 95) return infinity — they are impassable.
    Sub-blocked edges: intensity 0..94 → multiplier 0.5..2.85.
    """
    edge = graph["edges"][edge_idx]
    base = edge["distance_m"]
    if not overrides_map:
        return base
    edge_key = f'{edge["from"]}_{edge["to"]}'
    if edge_key not in overrides_map:
        return base
    intensity = overrides_map[edge_key]
    if intensity >= 95:
        return float("inf")
    # 0 = free flowing (bonus), 94 = severe penalty
    multiplier = 0.5 + (intensity / 100.0) * 2.5
    return base * multiplier


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


def nearest_node(graph: dict, lat: float, lon: float) -> str:
    """Find the graph node closest to a lat/lon coordinate."""
    from src.graph.builder import haversine

    best_id = None
    best_dist = float("inf")
    for nid, node in graph["nodes"].items():
        d = haversine(lat, lon, node["lat"], node["lon"])
        if d < best_dist:
            best_dist = d
            best_id = nid
    if best_id is None:
        raise ValueError("Graph has no nodes")
    return best_id
