"""H-13: event-driven closures (Lifeball, marathon, opera ball, etc.)."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_EVENTS = [
    {
        "name": "Vienna City Marathon",
        "date": "2026-04-19",
        "hours": [6, 15],
        "zones": ["1", "2", "3", "4", "9"],
        "multiplier": 2.50,
    },
    {
        "name": "Lifeball",
        "date": "2026-06-13",
        "hours": [18, 26],
        "zones": ["1"],
        "multiplier": 1.80,
    },
    {
        "name": "Opernball",
        "date": "2026-02-12",
        "hours": [18, 26],
        "zones": ["1"],
        "multiplier": 1.60,
    },
]

_EVENTS_CACHE: list[dict] | None = None


def _load_events() -> list[dict]:
    global _EVENTS_CACHE
    if _EVENTS_CACHE is not None:
        return _EVENTS_CACHE
    p = Path("data/events_2026.json")
    if p.exists():
        try:
            with open(p) as f:
                _EVENTS_CACHE = json.load(f)
                return _EVENTS_CACHE
        except Exception:
            pass
    _EVENTS_CACHE = DEFAULT_EVENTS
    return _EVENTS_CACHE


def get_active_events(date: str) -> list[dict]:
    return [e for e in _load_events() if e["date"] == date]


def get_event_multiplier(date: str, hour: int, goal_district: str) -> float:
    active = get_active_events(date)
    if not active:
        return 1.0
    mult = 1.0
    for e in active:
        start, end = e["hours"]
        in_window = start <= hour < end or (end > 24 and hour < end - 24)
        if in_window and goal_district in e["zones"]:
            mult = max(mult, e["multiplier"])
    return mult
