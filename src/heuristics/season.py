"""H-19: season multiplier (tourist density proxy)."""
from __future__ import annotations


def get_season_multiplier(month: int, goal_district: str) -> float:
    # Summer (Jun–Aug) tourist peak in inner districts
    if month in (6, 7, 8) and goal_district in ("1", "6", "7"):
        return 1.15
    # Advent / Christmas markets (Nov–Dec)
    if month in (11, 12) and goal_district in ("1", "6", "7", "8"):
        return 1.25
    # Winter (Jan–Feb) outer districts quieter
    if month in (1, 2) and goal_district not in ("1",):
        return 0.95
    return 1.0
