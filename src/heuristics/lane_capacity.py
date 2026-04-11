"""H-20: lane-count capacity bonus (car, bus, truck)."""
from __future__ import annotations


def get_lane_multiplier(edge: dict, vehicle: str) -> float:
    if vehicle not in ("car", "bus", "truck", "taxi"):
        return 1.0
    lanes = edge.get("lanes", 1)
    if lanes >= 4:
        return 0.90
    if lanes >= 3:
        return 0.95
    if lanes <= 1:
        return 1.10
    return 1.0
