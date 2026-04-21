"""
Road-quality multiplier — POSITIVE heuristic.

Returns <1 for fast/smooth roads so A* / Dijkstra prefer a longer path on a
good road over a shorter path on a bad one. Returned value multiplies the
edge's distance_m to yield a travel-time-equivalent cost (g-side).

Tuned so primary/secondary arterials beat residential/footway detours of up
to ~1.7x the raw distance. Never returns 0 (would break ε-admissibility).
"""
from __future__ import annotations

_ROAD_TYPE_MULT = {
    "primary": 0.55,
    "secondary": 0.65,
    "secondary_link": 0.70,
    "tertiary": 0.80,
    "busway": 0.75,
    "unclassified": 0.90,
    "residential": 1.00,
    "living_street": 1.15,
    "cycleway": 1.10,
    "pedestrian": 1.30,
    "footway": 1.50,
    "path": 1.55,
    "corridor": 1.60,
    "steps": 2.50,
    "elevator": 3.00,
    "platform": 1.40,
    "tram": 1.00,
}

_SURFACE_MULT = {
    "asphalt": 0.95,
    "concrete": 1.00,
    "paved": 1.00,
    "paving_stones": 1.10,
    "cobblestone": 1.30,
    "sett": 1.25,
    "unpaved": 1.40,
    "gravel": 1.40,
    "dirt": 1.50,
    "ground": 1.45,
}


def get_road_quality_multiplier(edge: dict, vehicle: str | None = None) -> float:
    """Edge-cost multiplier. <1 = fast road, >1 = slow road."""
    road_type = edge.get("road_type", "")
    mult = _ROAD_TYPE_MULT.get(road_type, 1.0)

    surface = (edge.get("surface") or "").lower()
    if surface in _SURFACE_MULT:
        mult *= _SURFACE_MULT[surface]

    maxspeed = edge.get("maxspeed")
    if isinstance(maxspeed, (int, float)) and maxspeed > 0:
        # Normalize around 50 km/h city default. 70 → 0.85, 30 → 1.25
        mult *= max(0.6, min(1.5, 50.0 / float(maxspeed)))

    if edge.get("tram_track") and vehicle in ("bicycle", "escooter", "motorcycle"):
        mult *= 1.25

    # Clamp to avoid pathological inversions
    return max(0.4, min(2.5, mult))
