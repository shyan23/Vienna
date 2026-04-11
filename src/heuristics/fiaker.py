"""H-14: Fiaker (horse-drawn carriages) in 1st district during tourist hours."""
from __future__ import annotations


def get_fiaker_multiplier(goal_district: str, vehicle: str, hour: int) -> float:
    if vehicle not in ("car", "bicycle", "motorcycle"):
        return 1.0
    if goal_district != "1":
        return 1.0
    if 10 <= hour < 18:
        return 1.25
    return 1.0
