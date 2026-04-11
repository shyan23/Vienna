"""H (bonus): Nachtbus/Nightline bonus for transit at night."""
from __future__ import annotations


def get_nightnetwork_multiplier(vehicle: str, hour: int) -> float:
    if vehicle not in ("bus", "metro"):
        return 1.0
    if 0 <= hour < 5:
        return 1.30  # reduced night service
    return 1.0
