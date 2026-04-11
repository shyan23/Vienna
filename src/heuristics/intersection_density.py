"""H-01: intersection density — penalise nodes with many connecting roads."""
from __future__ import annotations

ZONE_MULTIPLIERS = {
    "1": 1.30, "2": 1.10, "3": 1.10,
    "6": 1.15, "7": 1.20, "8": 1.20,
}


def get_intersection_penalty(node_id: str, graph: dict) -> float:
    degree = len(graph["adjacency"].get(node_id, []))
    if degree <= 2:
        return 1.0
    base = 1.0 + (degree - 2) * 0.05
    node = graph["nodes"].get(node_id, {})
    if node.get("has_traffic_signal"):
        base += 0.10
    district = node.get("district", "unknown")
    return base * ZONE_MULTIPLIERS.get(district, 1.0)
