"""HTTP API for the Vienna Traffic Router."""
from __future__ import annotations

import logging
import os
import traceback

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

log = logging.getLogger("api")

router = APIRouter()


class FindPathRequest(BaseModel):
    start_lat: float
    start_lon: float
    goal_lat: float
    goal_lon: float

    weather: str = "clear"
    hour: int = 12
    minute: int = 0
    day_of_week: int = 1          # 0=Mon … 6=Sun
    month: int = 4
    date: str = "2026-04-11"

    vehicle_type: str = "car"

    temperature: float = 15.0
    humidity: float = 60.0
    visibility_m: float = 5000.0
    wind_speed: float = 3.0
    wind_deg: float = 180.0

    enabled_heuristics: list[str] = []
    manual_overrides: list[dict] = []
    w: float = 1.5  # Weighted A* weight


class ManualOverrideRequest(BaseModel):
    edge_id: str
    intensity: int   # 0–100


# In-memory store for manual overrides (edge_id -> intensity 0..100)
_overrides: dict[str, int] = {}


@router.post("/find-path")
async def find_path(req: FindPathRequest):
    try:
        from src.algorithms.runner import run_all
        from src.heuristics.combined import make_heuristic

        log.info("find-path  start=(%.5f,%.5f)  goal=(%.5f,%.5f)  weather=%s",
                 req.start_lat, req.start_lon, req.goal_lat, req.goal_lon, req.weather)

        params = req.model_dump()
        # Merge persistent overrides with per-request overrides (weather events, boost)
        merged = dict(_overrides)
        for ov in (req.manual_overrides or []):
            if isinstance(ov, dict) and "edge_id" in ov:
                merged[ov["edge_id"]] = ov.get("intensity", 50)
        params["manual_overrides_map"] = merged

        heuristic_fn = make_heuristic(params)
        result = run_all(
            req.start_lat, req.start_lon,
            req.goal_lat, req.goal_lon,
            params,
            heuristic_fn,
        )
        return result
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        log.error("find-path FAILED: %s\n%s", e, tb)
        return JSONResponse(status_code=500, content={"error": str(e), "traceback": tb})


@router.post("/manual-override")
async def manual_override(req: ManualOverrideRequest):
    _overrides[req.edge_id] = req.intensity
    return {"status": "ok", "overrides_active": len(_overrides)}


@router.delete("/manual-override")
async def clear_overrides():
    _overrides.clear()
    return {"status": "cleared"}


@router.get("/weather")
async def get_weather():
    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "")
    fallback = {
        "weather": "clear",
        "temp": 15.0,
        "humidity": 60,
        "wind_speed": 3.0,
        "wind_deg": 180,
        "visibility": 5000,
        "description": "offline fallback",
    }
    if not api_key:
        return {**fallback, "source": "fallback"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": "Vienna,AT", "appid": api_key, "units": "metric"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:  # noqa: BLE001
        return {**fallback, "source": "error", "error": str(e)}

    weather_id = data["weather"][0]["id"]
    if weather_id >= 600:
        condition = "snow"
    elif weather_id >= 500:
        condition = "rain"
    elif weather_id >= 300:
        condition = "light_rain"
    elif weather_id >= 200:
        condition = "thunderstorm"
    elif weather_id == 741:
        condition = "fog"
    else:
        condition = "clear"

    return {
        "weather": condition,
        "temp": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"],
        "wind_deg": data["wind"].get("deg", 0),
        "visibility": data.get("visibility", 5000),
        "description": data["weather"][0]["description"],
        "source": "owm",
    }


@router.get("/graph/stats")
async def graph_stats():
    from src.graph.loader import load_graph

    g = load_graph()
    return g["meta"]


@router.get("/graph/bbox")
async def graph_bbox():
    from src.graph.loader import load_graph

    g = load_graph()
    return {"bbox": g["meta"]["bbox"]}


@router.get("/events/{date}")
async def get_events(date: str):
    try:
        from src.heuristics.events import get_active_events

        return {"events": get_active_events(date)}
    except Exception:
        return {"events": []}


@router.get("/health")
async def health():
    return {"status": "ok"}
