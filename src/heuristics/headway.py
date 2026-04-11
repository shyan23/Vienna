"""H-06: transit line headway (metro, train) — peak/off-peak frequency."""
from __future__ import annotations

LINE_HEADWAY_MIN = {
    "U1": (3, 7), "U2": (4, 8), "U3": (3, 7),
    "U4": (4, 8), "U5": (5, 10), "U6": (3, 8),
    "S1": (10, 30), "S2": (10, 30), "S3": (15, 30),
}


def get_headway_multiplier(vehicle: str, hour: int) -> float:
    if vehicle not in ("metro", "train"):
        return 1.0
    is_peak = 7 <= hour < 9 or 16 <= hour < 19
    sample = (3, 7) if vehicle == "metro" else (10, 30)
    wait = sample[0] if is_peak else sample[1]
    # Treat each minute of wait as +2% penalty baseline
    return 1.0 + wait * 0.02
