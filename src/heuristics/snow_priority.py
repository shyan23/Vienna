"""H-15: MA48 snow-clearing priority tiers."""
from __future__ import annotations


def get_snow_multiplier(edge: dict, weather: str) -> float:
    if weather not in ("snow", "heavy_snow", "light_snow", "black_ice"):
        return 1.0
    prio = edge.get("snow_priority", "B")
    if prio == "A":
        return 1.05  # cleared quickly
    return 1.60      # neighbourhood road — still slushy
