"""H-12: Austrian public holidays + tourist-day adjustments."""
from __future__ import annotations

AUSTRIAN_HOLIDAYS_2026 = {
    "2026-01-01": "Neujahr",
    "2026-01-06": "Heilige Drei Könige",
    "2026-04-06": "Ostermontag",
    "2026-05-01": "Staatsfeiertag",
    "2026-05-14": "Christi Himmelfahrt",
    "2026-05-25": "Pfingstmontag",
    "2026-06-04": "Fronleichnam",
    "2026-08-15": "Mariä Himmelfahrt",
    "2026-10-26": "Nationalfeiertag",
    "2026-11-01": "Allerheiligen",
    "2026-12-08": "Mariä Empfängnis",
    "2026-12-25": "Christtag",
    "2026-12-26": "Stefanitag",
}


def is_holiday(date: str) -> bool:
    return date in AUSTRIAN_HOLIDAYS_2026


def get_holiday_multiplier(date: str, goal_district: str) -> float:
    if not is_holiday(date):
        return 1.0
    # Inner districts see tourist foot traffic; outer districts quiet
    if goal_district in ("1", "6", "7", "8"):
        return 1.20
    return 0.80
