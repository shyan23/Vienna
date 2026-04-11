"""H-21: Baustellen (road works) from data/road_works_2026.json."""
from __future__ import annotations

import json
from pathlib import Path

from src.graph.builder import haversine

DEFAULT_ROAD_WORKS: list[dict] = []
_CACHE: list[dict] | None = None


def _load() -> list[dict]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    p = Path("data/road_works_2026.json")
    if p.exists():
        try:
            with open(p) as f:
                _CACHE = json.load(f)
                return _CACHE
        except Exception:
            pass
    _CACHE = DEFAULT_ROAD_WORKS
    return _CACHE


def get_road_works_multiplier(lat: float, lon: float, date: str) -> float:
    mult = 1.0
    for rw in _load():
        if not (rw.get("start_date", "") <= date <= rw.get("end_date", "")):
            continue
        if haversine(lat, lon, rw["lat"], rw["lon"]) < rw.get("radius_m", 150):
            mult = max(mult, rw.get("multiplier", 1.5))
    return mult
