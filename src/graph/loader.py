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
