"""H-08: wind penalty for cyclists and pedestrians (headwind)."""
from __future__ import annotations

import math


def get_wind_multiplier(vehicle: str, wind_speed: float, wind_deg: float, heading_deg: float = 0) -> float:
    if vehicle not in ("bicycle", "walking", "escooter"):
        return 1.0
    if wind_speed < 3:
        return 1.0
    # Simplified: strong headwind estimated via cosine alignment to heading.
    delta = math.radians(abs((wind_deg - heading_deg + 180) % 360 - 180))
    headwind_component = wind_speed * math.cos(delta)
    if headwind_component <= 0:
        return 1.0
    factor = 0.03 if vehicle == "bicycle" else 0.02
    return 1.0 + headwind_component * factor
