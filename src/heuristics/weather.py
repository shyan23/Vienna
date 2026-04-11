"""Weather multiplier lookup + black-ice inference."""
from __future__ import annotations

WEATHER_MULTIPLIERS = {
    "clear":         1.00,
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


def get_weather_multiplier(weather: str) -> float:
    return WEATHER_MULTIPLIERS.get(weather, 1.0)


def infer_black_ice(temp: float, humidity: float, weather: str) -> str:
    """Promote clear/fog to black_ice risk when cold + humid."""
    if temp < 2 and humidity > 80 and weather in ("clear", "cloudy", "fog"):
        return "black_ice"
    return weather
