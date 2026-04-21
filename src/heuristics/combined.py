"""
Composite heuristic factory.

make_heuristic(params) returns a closure h(node_id, goal_id, graph, params)
that multiplies the Haversine distance by the product of all active heuristics.

Two tiers:

  1. Static multipliers — computed ONCE at closure build time (weather,
     time-of-day, vehicle, parking, holiday, season, event, visibility,
     night network, humidity, delivery). These depend only on the params,
     not on the current node/edge, so we bake them into a single float.

  2. Dynamic multipliers — evaluated per-call on the frontier node. These
     depend on the edge from the predecessor and on the current node
     (intersection density, surface, elevation, safety, emission,
     tram_tracks, snow, bridges, markets, heuriger, lane capacity,
     school zones, fiaker, pedestrian density, road works, manual override).

The output is capped at MAX_HEURISTIC_CAP × the raw Haversine distance, so
weighted A* remains bounded-suboptimal rather than arbitrarily inadmissible.
"""
from __future__ import annotations

import os
from typing import Callable

from src.graph.builder import haversine
from src.heuristics.commuter_bridges import get_bridge_multiplier
from src.heuristics.delivery import get_delivery_multiplier
from src.heuristics.elevation import get_elevation_multiplier
from src.heuristics.emission_zones import get_emission_multiplier
from src.heuristics.events import get_event_multiplier
from src.heuristics.fiaker import get_fiaker_multiplier
from src.heuristics.headway import get_headway_multiplier
from src.heuristics.heuriger import get_heuriger_multiplier
from src.heuristics.holiday_historical import get_holiday_multiplier
from src.heuristics.humidity import get_humidity_multiplier
from src.heuristics.intersection_density import get_intersection_penalty
from src.heuristics.lane_capacity import get_lane_multiplier
from src.heuristics.manual_adjustment import get_manual_multiplier
from src.heuristics.markets import get_market_multiplier
from src.heuristics.nightnetwork import get_nightnetwork_multiplier
from src.heuristics.parking import get_parking_multiplier
from src.heuristics.pedestrian_density import get_pedestrian_multiplier
from src.heuristics.road_quality import get_road_quality_multiplier
from src.heuristics.road_works import get_road_works_multiplier
from src.heuristics.safety import get_safety_multiplier
from src.heuristics.scenic import get_scenic_multiplier
from src.heuristics.school_zones import get_school_multiplier
from src.heuristics.season import get_season_multiplier
from src.heuristics.snow_priority import get_snow_multiplier
from src.heuristics.surface import get_surface_multiplier
from src.heuristics.time_of_day import get_time_multiplier
from src.heuristics.tram_tracks import get_tram_track_multiplier
from src.heuristics.vehicle_type import get_vehicle_multiplier
from src.heuristics.visibility import get_visibility_multiplier
from src.heuristics.weather import get_weather_multiplier, infer_black_ice
from src.heuristics.wind import get_wind_multiplier

MAX_HEURISTIC_CAP = float(os.getenv("MAX_HEURISTIC_CAP", "50.0"))

# Set of all heuristic IDs the UI can toggle.
ALL_HEURISTIC_IDS = {
    "weather", "time_of_day", "vehicle_type", "intersection_density",
    "surface", "elevation", "safety", "emission_zones", "headway",
    "tram_tracks", "wind", "parking", "scenic", "school_zones",
    "holiday_historical", "events", "fiaker", "snow_priority",
    "commuter_bridges", "markets", "heuriger", "season",
    "lane_capacity", "road_works", "humidity", "visibility",
    "pedestrian_density", "delivery", "nightnetwork",
    "manual_adjustment", "road_quality",
}


def base_heuristic(node_id: str, goal_id: str, graph: dict, params: dict) -> float:
    """Pure admissible Haversine — used when make_heuristic is skipped."""
    node = graph["nodes"][node_id]
    goal = graph["nodes"][goal_id]
    return haversine(node["lat"], node["lon"], goal["lat"], goal["lon"])


def _enabled(enabled: set[str], key: str) -> bool:
    # Empty enabled set == all active (default behaviour for the UI's baseline)
    return not enabled or key in enabled


def make_heuristic(params: dict) -> Callable:
    """Return a closure tuned to the given request params."""
    enabled: set[str] = set(params.get("enabled_heuristics", []) or [])
    vehicle: str = params.get("vehicle_type", "car")
    hour: int = int(params.get("hour", 12))
    minute: int = int(params.get("minute", 0))
    day_of_week: int = int(params.get("day_of_week", 1))
    month: int = int(params.get("month", 4))
    date: str = params.get("date", "2026-04-11")
    profile: str = params.get("route_profile", "fastest")
    wind_speed: float = float(params.get("wind_speed", 3.0))
    wind_deg: float = float(params.get("wind_deg", 180.0))
    visibility_m: float = float(params.get("visibility_m", 5000))
    humidity: float = float(params.get("humidity", 60))
    overrides: dict[str, int] = params.get("manual_overrides_map") or {}

    # Resolve weather (promote to black_ice when the conditions align)
    weather = infer_black_ice(
        float(params.get("temperature", 15.0)),
        humidity,
        params.get("weather", "clear"),
    )

    # ---------------- static multiplier (closure-built once) ---------------- #
    static_mult = 1.0

    if _enabled(enabled, "weather"):
        static_mult *= get_weather_multiplier(weather)
    if _enabled(enabled, "time_of_day"):
        static_mult *= get_time_multiplier(hour, day_of_week)
    if _enabled(enabled, "vehicle_type"):
        static_mult *= get_vehicle_multiplier(vehicle)
    if _enabled(enabled, "visibility"):
        static_mult *= get_visibility_multiplier(visibility_m)
    if _enabled(enabled, "humidity"):
        static_mult *= get_humidity_multiplier(humidity, vehicle)
    if _enabled(enabled, "nightnetwork"):
        static_mult *= get_nightnetwork_multiplier(vehicle, hour)
    if _enabled(enabled, "wind"):
        static_mult *= get_wind_multiplier(vehicle, wind_speed, wind_deg)
    if _enabled(enabled, "headway"):
        static_mult *= get_headway_multiplier(vehicle, hour)

    def heuristic(node_id: str, goal_id: str, graph: dict, _params: dict = None) -> float:
        nodes = graph["nodes"]
        node = nodes[node_id]
        goal = nodes[goal_id]
        h_base = haversine(node["lat"], node["lon"], goal["lat"], goal["lon"])
        if h_base == 0:
            return 0.0

        goal_district = goal.get("district", "unknown")
        mult = static_mult

        # ---- goal-only multipliers (constant per route but need goal) ---- #
        if _enabled(enabled, "parking"):
            mult *= get_parking_multiplier(goal_district, vehicle)
        if _enabled(enabled, "holiday_historical"):
            mult *= get_holiday_multiplier(date, goal_district)
        if _enabled(enabled, "events"):
            mult *= get_event_multiplier(date, hour, goal_district)
        if _enabled(enabled, "fiaker"):
            mult *= get_fiaker_multiplier(goal_district, vehicle, hour)
        if _enabled(enabled, "season"):
            mult *= get_season_multiplier(month, goal_district)
        if _enabled(enabled, "pedestrian_density"):
            mult *= get_pedestrian_multiplier(goal_district, vehicle, hour, date)
        if _enabled(enabled, "delivery"):
            mult *= get_delivery_multiplier(goal_district, vehicle, hour)

        # ---- node-dependent ---- #
        if _enabled(enabled, "intersection_density"):
            mult *= get_intersection_penalty(node_id, graph)
        if _enabled(enabled, "road_works"):
            mult *= get_road_works_multiplier(node["lat"], node["lon"], date)
        if _enabled(enabled, "markets"):
            mult *= get_market_multiplier(node["lat"], node["lon"], day_of_week, hour)
        if _enabled(enabled, "heuriger"):
            mult *= get_heuriger_multiplier(node["lat"], node["lon"], month, day_of_week, hour)

        # ---- edge-dependent (pick the cheapest outgoing edge as a proxy) ---- #
        adj = graph["adjacency"].get(node_id, [])
        if adj:
            edges = graph["edges"]
            best_edge_mult = float("inf")
            for nb in adj:
                edge = edges[nb["edge_idx"]]
                e_mult = 1.0
                if _enabled(enabled, "surface"):
                    e_mult *= get_surface_multiplier(edge, vehicle)
                if _enabled(enabled, "elevation"):
                    e_mult *= get_elevation_multiplier(edge, vehicle)
                if _enabled(enabled, "safety"):
                    e_mult *= get_safety_multiplier(edge, hour, vehicle)
                if _enabled(enabled, "emission_zones"):
                    e_mult *= get_emission_multiplier(edge, vehicle)
                if _enabled(enabled, "tram_tracks"):
                    e_mult *= get_tram_track_multiplier(edge, vehicle, weather)
                if _enabled(enabled, "snow_priority"):
                    e_mult *= get_snow_multiplier(edge, weather)
                if _enabled(enabled, "commuter_bridges"):
                    e_mult *= get_bridge_multiplier(edge, hour, day_of_week)
                if _enabled(enabled, "lane_capacity"):
                    e_mult *= get_lane_multiplier(edge, vehicle)
                if _enabled(enabled, "school_zones"):
                    e_mult *= get_school_multiplier(edge, hour, minute, day_of_week)
                if _enabled(enabled, "scenic"):
                    e_mult *= get_scenic_multiplier(edge, profile)
                if _enabled(enabled, "road_quality"):
                    e_mult *= get_road_quality_multiplier(edge, vehicle)
                if _enabled(enabled, "manual_adjustment"):
                    edge_key = f"{edge['from']}_{edge['to']}"
                    e_mult *= get_manual_multiplier(edge_key, overrides)
                if e_mult < best_edge_mult:
                    best_edge_mult = e_mult
            if best_edge_mult != float("inf"):
                mult *= best_edge_mult

        h = h_base * mult
        # Cap total h against arbitrary blow-up, keep ε-admissibility
        return min(h, h_base * MAX_HEURISTIC_CAP)

    return heuristic
