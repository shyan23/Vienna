"""H-10: scenic corridor bonus — greenest profile only."""
from __future__ import annotations


def get_scenic_multiplier(edge: dict, profile: str) -> float:
    if profile != "greenest":
        return 1.0
    return 0.85 if edge.get("near_green_space") else 1.05
