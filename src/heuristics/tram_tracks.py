"""H-07: tram-track penalty (bicycle) — slippery when wet."""
from __future__ import annotations


def get_tram_track_multiplier(edge: dict, vehicle: str, weather: str) -> float:
    if vehicle != "bicycle":
        return 1.0
    if not edge.get("tram_track"):
        return 1.0
    if weather in ("rain", "heavy_rain", "light_rain", "snow", "heavy_snow", "black_ice"):
        return 1.70
    return 1.25
