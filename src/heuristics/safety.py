"""H-04: night safety — prefer lit primary roads between 21:00 and 05:00."""
from __future__ import annotations


def get_safety_multiplier(edge: dict, hour: int, vehicle: str) -> float:
    if vehicle != "walking":
        return 1.0
    if not (hour >= 21 or hour < 5):
        return 1.0
    lit = edge.get("lit", "unknown")
    rt = edge.get("road_type", "")
    if lit != "yes":
        return 1.5
    if rt in ("primary", "secondary", "tertiary"):
        return 0.9  # actively preferred
    return 1.1
