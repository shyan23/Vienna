"""H-17: Saturday open-air market zones."""
from __future__ import annotations

from src.graph.builder import haversine

MARKETS = [
    # (lat, lon, radius_m, active_day, (start_h, end_h))
    (48.2197, 16.3453, 200, 5, (8, 13)),    # Brunnenmarkt
    (48.2145, 16.3845, 200, 5, (6, 14)),    # Karmelitermarkt
    (48.1988, 16.3635, 250, -1, (6, 19)),   # Naschmarkt (daily)
    (48.2030, 16.3925, 200, 5, (6, 13)),    # Rochusmarkt
    (48.2013, 16.3378, 200, 5, (8, 13)),    # Yppenplatz
]


def get_market_multiplier(lat: float, lon: float, day_of_week: int, hour: int) -> float:
    for (mlat, mlon, radius, day, (h1, h2)) in MARKETS:
        if day != -1 and day_of_week != day:
            continue
        if not (h1 <= hour < h2):
            continue
        if haversine(lat, lon, mlat, mlon) < radius:
            return 1.45
    return 1.0
