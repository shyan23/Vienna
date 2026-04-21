"""
Speed-preference multiplier — POSITIVE heuristic.

At speed_weight=0 (default): returns 1.0, no effect.
At speed_weight=1.0: primary (60 km/h) → 0.50, motorway (100 km/h) → 0.30.

Only gives bonuses (<1.0) for roads faster than the 30 km/h city baseline.
Slow roads (residential, footway) are left at 1.0 — never penalised here.

Effect: A* and Greedy will prefer a longer route on a fast arterial over
a shorter route on slow backstreets when speed_weight > 0.
"""
from __future__ import annotations

_ROAD_SPEED_KMH: dict[str, float] = {
    "motorway":       100.0,
    "motorway_link":   70.0,
    "trunk":           80.0,
    "trunk_link":      60.0,
    "primary":         60.0,
    "primary_link":    50.0,
    "secondary":       50.0,
    "secondary_link":  40.0,
    "tertiary":        40.0,
    "tertiary_link":   35.0,
    "busway":          40.0,
}

_BASE_SPEED = 30.0  # city-default km/h — residential treated as neutral


def get_speed_preference_multiplier(edge: dict, speed_weight: float) -> float:
    """Return <1.0 bonus for fast roads scaled by speed_weight (0.0–1.0)."""
    if speed_weight <= 0.0:
        return 1.0
    road_type = edge.get("road_type", "")
    road_speed = _ROAD_SPEED_KMH.get(road_type, _BASE_SPEED)
    if road_speed <= _BASE_SPEED:
        return 1.0  # residential/footway/cycleway — no bonus here
    # time_ratio = BASE / road_speed: primary→0.50, motorway→0.30
    time_ratio = _BASE_SPEED / road_speed
    # blend: weight=0 → 1.0, weight=1 → time_ratio
    return 1.0 - speed_weight * (1.0 - time_ratio)
