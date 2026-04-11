"""Vehicle-type multiplier + forbidden road-type filter."""
from __future__ import annotations

from typing import Callable

VEHICLE_MULTIPLIERS = {
    "car":        1.00,
    "motorcycle": 0.85,
    "taxi":       1.05,
    "bus":        1.30,
    "metro":      0.40,
    "train":      0.45,
    "walking":    1.80,
    "bicycle":    1.20,
    "truck":      1.60,
    "escooter":   1.30,
}

FORBIDDEN_ROAD_TYPES: dict[str, Callable[[str], bool]] = {
    "metro":    lambda rt: rt not in ("subway", "light_rail"),
    "train":    lambda rt: rt not in ("rail", "light_rail"),
    "walking":  lambda rt: rt in ("motorway", "trunk"),
    "bicycle":  lambda rt: rt in ("motorway", "trunk"),
    "escooter": lambda rt: rt in ("motorway", "trunk", "steps"),
    "bus":      lambda rt: rt in ("cycleway", "footway", "steps", "pedestrian"),
}


def get_vehicle_multiplier(vehicle: str) -> float:
    return VEHICLE_MULTIPLIERS.get(vehicle, 1.0)


def is_forbidden_for_vehicle(road_type: str, vehicle: str) -> bool:
    check = FORBIDDEN_ROAD_TYPES.get(vehicle)
    return check(road_type) if check else False
