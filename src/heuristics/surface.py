"""H-02: pavement / surface material penalty (vehicle-dependent)."""
from __future__ import annotations

SURFACE_PENALTIES = {
    "cobblestone": {"car": 1.05, "motorcycle": 1.10, "bicycle": 1.60, "walking": 1.10, "bus": 1.15, "escooter": 1.70},
    "sett":        {"car": 1.03, "motorcycle": 1.05, "bicycle": 1.40, "walking": 1.05, "bus": 1.10, "escooter": 1.50},
    "unpaved":     {"car": 1.15, "motorcycle": 1.20, "bicycle": 1.80, "walking": 1.20, "bus": 1.30, "escooter": 2.00},
    "gravel":      {"car": 1.15, "motorcycle": 1.20, "bicycle": 1.80, "walking": 1.20, "bus": 1.30, "escooter": 2.00},
    "metal":       {"car": 1.10, "motorcycle": 1.30, "bicycle": 1.90, "walking": 1.20, "bus": 1.00, "escooter": 2.00},
    "wood":        {"car": 1.05, "motorcycle": 1.20, "bicycle": 1.50, "walking": 1.10, "bus": 1.05, "escooter": 1.80},
}


def get_surface_multiplier(edge: dict, vehicle: str) -> float:
    surface = edge.get("surface", "asphalt")
    if surface in ("asphalt", "paved", "concrete"):
        return 1.0
    return SURFACE_PENALTIES.get(surface, {}).get(vehicle, 1.0)
