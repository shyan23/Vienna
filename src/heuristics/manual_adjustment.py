"""Manual road-override multiplier (from the UI traffic slider)."""
from __future__ import annotations


def get_manual_multiplier(edge_key: str, overrides: dict[str, int]) -> float:
    """intensity 0..100 → multiplier 0.5..3.0."""
    if edge_key not in overrides:
        return 1.0
    intensity = overrides[edge_key]
    # 0 = free flowing (bonus), 100 = jam (severe penalty)
    return 0.5 + (intensity / 100.0) * 2.5
