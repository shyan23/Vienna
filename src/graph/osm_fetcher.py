"""
OSM Overpass API fetcher.
Handles retries, mirrors, caching, and response validation.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

# south, west, north, east
VIENNA_BBOX = (48.118, 16.183, 48.324, 16.578)

OVERPASS_QUERY = """
[out:json][timeout:180][bbox:{south},{west},{north},{east}];
(
  way["highway"]["highway"!~"service|track|bridleway"]["area"!="yes"];
  way["railway"~"subway|light_rail|tram"];
)->.ways;
node(w.ways)->.nodes;
(.ways; .nodes;);
out body;
""".strip()


def fetch_vienna_osm(cache_path: Path, max_age_days: int = 30) -> dict:
    """
    Download Vienna OSM data from Overpass, with local caching.

    If ``cache_path`` exists and is younger than ``max_age_days``, returns cached
    data. Otherwise downloads fresh data, saves it, and returns it.
    """
    cache_path = Path(cache_path)

    if cache_path.exists():
        age_days = (time.time() - cache_path.stat().st_mtime) / 86400
        if age_days < max_age_days:
            print(f"[OSM] Using cached data ({age_days:.1f} days old): {cache_path}")
            with open(cache_path) as f:
                return json.load(f)

    query = OVERPASS_QUERY.format(
        south=VIENNA_BBOX[0],
        west=VIENNA_BBOX[1],
        north=VIENNA_BBOX[2],
        east=VIENNA_BBOX[3],
    )

    last_err: Exception | None = None
    for i, mirror in enumerate(MIRRORS):
        try:
            print(f"[OSM] Fetching from mirror {i+1}/{len(MIRRORS)}: {mirror}")
            print("[OSM] This may take 30–90 seconds for Vienna...")
            resp = requests.post(mirror, data={"data": query}, timeout=200)
            resp.raise_for_status()
            data = resp.json()

            element_types = {e["type"] for e in data.get("elements", [])}
            if "node" not in element_types or "way" not in element_types:
                raise RuntimeError(
                    f"Response missing expected element types. Got: {element_types}"
                )

            node_count = sum(1 for e in data["elements"] if e["type"] == "node")
            way_count = sum(1 for e in data["elements"] if e["type"] == "way")
            print(f"[OSM] Downloaded: {node_count:,} nodes, {way_count:,} ways")

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(data, f)
            print(
                f"[OSM] Saved to {cache_path} "
                f"({cache_path.stat().st_size / 1e6:.1f} MB)"
            )
            return data

        except Exception as e:  # noqa: BLE001 — we want to try the next mirror
            print(f"[OSM] Mirror {i+1} failed: {e}")
            last_err = e
            if i < len(MIRRORS) - 1:
                time.sleep(5)

    raise RuntimeError(
        f"All Overpass mirrors failed. Check internet connection. Last error: {last_err}"
    )
