"""H-09: parking difficulty at destination district (car only)."""
from __future__ import annotations

DISTRICT_PARKING_PENALTY = {
    "1": 1.60, "2": 1.35, "3": 1.25, "4": 1.20, "5": 1.20,
    "6": 1.40, "7": 1.45, "8": 1.30, "9": 1.25,
}


def get_parking_multiplier(goal_district: str, vehicle: str) -> float:
    if vehicle not in ("car", "truck", "taxi"):
        return 1.0
    return DISTRICT_PARKING_PENALTY.get(goal_district, 1.05)
