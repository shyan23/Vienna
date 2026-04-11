"""H-16: Danube commuter bridge congestion (Reichsbrücke, Nordbrücke, …)."""
from __future__ import annotations

BRIDGE_RUSH_MULT = {
    "Reichsbrücke":       1.80,
    "Nordbrücke":         1.60,
    "Floridsdorfer Brücke": 1.50,
    "Stadionbrücke":      1.40,
    "Praterbrücke":       2.00,
}


def get_bridge_multiplier(edge: dict, hour: int, day_of_week: int) -> float:
    name = edge.get("name", "")
    if not any(k in name for k in BRIDGE_RUSH_MULT):
        return 1.0
    if day_of_week >= 5:
        return 1.0
    is_rush = 7 <= hour < 9 or 16 <= hour < 19
    if not is_rush:
        return 1.0
    for key, mult in BRIDGE_RUSH_MULT.items():
        if key in name:
            return mult
    return 1.0
