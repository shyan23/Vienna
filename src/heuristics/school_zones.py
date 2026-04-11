"""H-11: school drop-off / pickup windows — slow down near schools."""
from __future__ import annotations

SCHOOL_WINDOWS = [
    (7, 8, 15),   # 07:30-08:15 morning drop-off
    (13, 14, 0),  # 13:00-14:00 pickup
]


def is_school_window(hour: int, minute: int, day_of_week: int) -> bool:
    if day_of_week >= 5:
        return False
    for (start_h, end_h, end_m) in SCHOOL_WINDOWS:
        if hour == start_h and minute >= 30:
            return True
        if start_h < hour < end_h:
            return True
        if hour == end_h and minute <= end_m:
            return True
    return False


def get_school_multiplier(edge: dict, hour: int, minute: int, day_of_week: int) -> float:
    if not edge.get("near_school"):
        return 1.0
    return 1.35 if is_school_window(hour, minute, day_of_week) else 1.0
