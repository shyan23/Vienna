"""H (bonus): humidity comfort for walking / cycling."""
from __future__ import annotations


def get_humidity_multiplier(humidity: float, vehicle: str) -> float:
    if vehicle not in ("walking", "bicycle", "escooter"):
        return 1.0
    if humidity > 85:
        return 1.10
    if humidity < 20:
        return 1.05
    return 1.0
