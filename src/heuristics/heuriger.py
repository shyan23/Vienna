"""H-18: Heuriger (wine tavern) zones — Sep–Oct, Fri–Sat evenings."""
from __future__ import annotations

from src.graph.builder import haversine

HEURIGER_ZONES = [
    (48.2645, 16.3483, 400, "Grinzing"),
    (48.2450, 16.3250, 300, "Neustift am Walde"),
    (48.2883, 16.4217, 300, "Stammersdorf"),
    (48.1433, 16.3183, 300, "Mauer"),
]


def get_heuriger_multiplier(lat: float, lon: float, month: int, day_of_week: int, hour: int) -> float:
    if month not in (9, 10):
        return 1.0
    if day_of_week not in (4, 5):
        return 1.0
    if not (16 <= hour < 23):
        return 1.0
    for (hlat, hlon, radius, _name) in HEURIGER_ZONES:
        if haversine(lat, lon, hlat, hlon) < radius:
            return 1.35
    return 1.0
