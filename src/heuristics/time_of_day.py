"""Time-of-day rush-hour multiplier for Vienna."""
from __future__ import annotations

# (hour_start, hour_end, weekday_mult, weekend_mult)
TIME_SLOTS = [
    (0,  5,  0.70, 0.65),
    (5,  7,  1.00, 0.75),
    (7,  9,  1.60, 0.90),
    (9,  11, 1.10, 1.00),
    (11, 13, 1.30, 1.15),
    (13, 15, 1.10, 1.00),
    (15, 17, 1.40, 1.10),
    (17, 19, 1.70, 1.10),
    (19, 22, 1.20, 1.30),
    (22, 24, 0.80, 1.10),
]


def get_time_multiplier(hour: int, day_of_week: int) -> float:
    is_weekend = day_of_week >= 5
    for (start, end, wd, we) in TIME_SLOTS:
        if start <= hour < end:
            return we if is_weekend else wd
    return 1.0
