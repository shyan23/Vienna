"""H-22: pedestrian density in pedestrian-heavy zones (car / bicycle)."""
from __future__ import annotations

from src.heuristics.holiday_historical import is_holiday

PEDESTRIAN_ZONES = {
    "1": 1.35,   # Innere Stadt
    "6": 1.20,   # Mariahilf
    "7": 1.20,   # Neubau
    "8": 1.10,   # Josefstadt
}


def get_pedestrian_multiplier(goal_district: str, vehicle: str, hour: int, date: str) -> float:
    if vehicle not in ("car", "truck", "bicycle", "motorcycle"):
        return 1.0
    base = PEDESTRIAN_ZONES.get(goal_district, 1.0)
    if base == 1.0:
        return 1.0
    in_window = 11 <= hour < 20
    if not in_window:
        return 1.0
    if is_holiday(date):
        base *= 1.15
    return base
