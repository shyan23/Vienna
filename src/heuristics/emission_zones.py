"""H-05: emission / low-traffic zones — cars and trucks avoid motor_vehicle=no."""
from __future__ import annotations


def get_emission_multiplier(edge: dict, vehicle: str) -> float:
    if vehicle not in ("car", "truck", "taxi", "bus"):
        return 1.0
    mv = edge.get("motor_vehicle", "yes")
    if mv in ("no", "private", "destination"):
        return 8.0  # essentially forbidden
    return 1.0
