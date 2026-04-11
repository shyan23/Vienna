"""H-03: elevation / slope penalty (walking, cycling, bus)."""
from __future__ import annotations


def get_elevation_multiplier(edge: dict, vehicle: str) -> float:
    if vehicle not in ("walking", "bicycle", "bus", "escooter"):
        return 1.0
    e1 = edge.get("elevation_start_m")
    e2 = edge.get("elevation_end_m")
    if e1 is None or e2 is None:
        return 1.0
    dist = max(edge.get("distance_m", 1.0), 1.0)
    slope_pct = ((e2 - e1) / dist) * 100
    if slope_pct <= 0:
        return 1.0  # downhill / flat — no penalty
    # +5% penalty per 1% slope for bikes/walking, +3% for bus
    per = 0.03 if vehicle == "bus" else 0.05
    return 1.0 + slope_pct * per
