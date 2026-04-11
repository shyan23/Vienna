"""H (bonus): visibility — fog / low-light slowdown."""
from __future__ import annotations


def get_visibility_multiplier(visibility_m: float) -> float:
    if visibility_m >= 3000:
        return 1.0
    if visibility_m >= 1000:
        return 1.15
    if visibility_m >= 300:
        return 1.35
    return 1.60
