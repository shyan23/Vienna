"""H (bonus): delivery / loading-zone window (truck only)."""
from __future__ import annotations


def get_delivery_multiplier(goal_district: str, vehicle: str, hour: int) -> float:
    if vehicle != "truck":
        return 1.0
    # Vienna generally restricts HGV in centre 07:30-18:30
    if goal_district == "1" and 7 <= hour < 19:
        return 1.80
    return 1.0
