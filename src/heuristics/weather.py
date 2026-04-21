"""Weather multiplier lookup + black-ice inference.

`clear` has no entry — `.get(..., 1.0)` returns neutral so it contributes
nothing to the composite heuristic. Rain variants take an extra penalty
for exposed/slow modes (walking, bicycle, escooter) since puddles,
reduced grip, and visibility hit them much harder than motorised traffic.
"""
from __future__ import annotations

WEATHER_MULTIPLIERS = {
    "cloudy":        1.10,
    "light_rain":    1.25,
    "rain":          1.50,
    "heavy_rain":    1.55,
    "thunderstorm":  1.60,
    "fog":           1.30,
    "light_snow":    1.40,
    "snow":          1.60,
    "heavy_snow":    1.80,
    "black_ice":     2.00,
}

RAIN_VARIANTS = ("light_rain", "rain", "heavy_rain", "thunderstorm")

# Extra multiplier stacked on top of base rain penalty for exposed modes.
RAIN_VEHICLE_PENALTY = {
    "walking":  {"light_rain": 1.35, "rain": 1.70, "heavy_rain": 2.10, "thunderstorm": 2.30},
    "bicycle":  {"light_rain": 1.30, "rain": 1.60, "heavy_rain": 1.95, "thunderstorm": 2.20},
    "escooter": {"light_rain": 1.30, "rain": 1.65, "heavy_rain": 2.00, "thunderstorm": 2.25},
}


def get_weather_multiplier(weather: str, vehicle: str = "car") -> float:
    base = WEATHER_MULTIPLIERS.get(weather, 1.0)
    if weather in RAIN_VARIANTS:
        extra = RAIN_VEHICLE_PENALTY.get(vehicle, {}).get(weather, 1.0)
        return base * extra
    return base


def infer_black_ice(temp: float, humidity: float, weather: str) -> str:
    """Promote cloudy/fog to black_ice risk when cold + humid (clear is neutral)."""
    if temp < 2 and humidity > 80 and weather in ("clear", "cloudy", "fog"):
        return "black_ice"
    return weather
