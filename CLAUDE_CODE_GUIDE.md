# Vienna Traffic Router — Claude Code Build Guide

> **How to use this document:** Hand this file to Claude Code. It is written as a
> series of numbered checkpoints. Run one checkpoint at a time, verify it works,
> then proceed. Each checkpoint produces a testable deliverable. You can stop,
> adjust, and re-read at any point.

---

## Project Summary

You are building a web application that:

1. Downloads Vienna's road network from OpenStreetMap (~1 000 nodes, ~10 000 edges
   — a curated, tractable subgraph)
2. Runs 8 classic AI search algorithms (BFS, DFS, UCS, Dijkstra, Greedy, A\*,
   Weighted A\*, Bidirectional A\*) on that graph in parallel
3. Shows all 8 routes simultaneously on an interactive Leaflet map of Vienna
4. Lets the user tune 22+ heuristic parameters (weather, time of day, vehicle type,
   Vienna-specific local effects) and watch the routes change in real time
5. Presents a beautiful dark-mode UI with an algorithm comparison table,
   live heuristic weight bars, and a rich overlay system. Use Pencil.dev or stich(google) for UI
   design. Also make sure i can see the map view of vienna, you can use some cool icon for interesting place; keep the color soothing,and for differen seasons, please add themes of different themes

**Tech stack:** Python 3.11+ / FastAPI (backend) · Vanilla JS + Leaflet.js (frontend)
· OpenStreetMap Overpass API (data) · OpenWeatherMap free tier (weather)

---

## Repository Layout (target)

```
vienna-traffic-router/
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
│
├── scripts/
│   ├── fetch_osm_data.py       ← OSM download + graph construction
│   └── precompute_elevation.py ← SRTM elevation baking (Sprint 4)
│
├── data/                       ← generated, gitignored
│   ├── vienna_raw.json
│   ├── vienna_graph.json
│   ├── vienna_distances.json
│   ├── events_2026.json
│   └── road_works_2026.json
│
├── src/
│   ├── main.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── builder.py
│   │   └── osm_fetcher.py
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── base.py             ← PathResult + SearchAlgorithm Protocol
│   │   ├── bfs.py
│   │   ├── dfs.py
│   │   ├── ucs.py
│   │   ├── dijkstra.py
│   │   ├── greedy_best_first.py
│   │   ├── astar.py
│   │   ├── weighted_astar.py
│   │   ├── bidirectional_astar.py
│   │   └── runner.py
│   ├── heuristics/
│   │   ├── __init__.py
│   │   ├── weather.py
│   │   ├── time_of_day.py
│   │   ├── manual_adjustment.py
│   │   ├── holiday_historical.py
│   │   ├── vehicle_type.py
│   │   ├── surface.py
│   │   ├── elevation.py
│   │   ├── safety.py
│   │   ├── emission_zones.py
│   │   ├── intersection_density.py
│   │   ├── headway.py
│   │   ├── tram_tracks.py
│   │   ├── wind.py
│   │   ├── parking.py
│   │   ├── scenic.py
│   │   ├── events.py
│   │   ├── school_zones.py
│   │   ├── fiaker.py
│   │   ├── snow_priority.py
│   │   ├── commuter_bridges.py
│   │   ├── markets.py
│   │   ├── heuriger.py
│   │   ├── season.py
│   │   ├── lane_capacity.py
│   │   ├── road_works.py
│   │   ├── humidity.py
│   │   ├── visibility.py
│   │   ├── pedestrian_density.py
│   │   ├── delivery.py
│   │   ├── nightnetwork.py
│   │   └── combined.py
│   └── routes/
│       └── api.py
│
└── public/
    ├── index.html
    ├── css/
    │   └── style.css
    └── js/
        ├── app.js
        ├── map.js
        ├── sidebar.js
        ├── overlays.js
        ├── results.js
        ├── explainer.js
        ├── presets.js
        └── api.js
```

---

## Environment Setup (do once, before any sprint)

```bash
# 1. Create project root
mkdir vienna-traffic-router && cd vienna-traffic-router

# 2. Python virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install fastapi uvicorn httpx pydantic python-dotenv requests numpy

# 4. Create .env
cat > .env << 'EOF'
OPENWEATHERMAP_API_KEY=your_key_here
VIENNA_GRAPH_PATH=data/vienna_graph.json
MAX_HEURISTIC_CAP=50.0
ALGORITHM_TIMEOUT_MS=2000
EOF

# 5. Create data directory
mkdir -p data public/css public/js src/algorithms src/heuristics src/graph src/routes scripts

# 6. .gitignore
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
.env
data/
*.egg-info/
EOF
```

**Get a free OpenWeatherMap key:** https://openweathermap.org/api → sign up → API keys.
The free tier gives 1 000 calls/day — more than enough.

---

---

# CHECKPOINT 0 — Understanding the Data Pipeline

> **Read this section carefully before Sprint 1. It explains exactly where the graph
> data comes from, what you are downloading, and how large it will be.**

---

## 0.1 What is OpenStreetMap Overpass API?

OpenStreetMap (OSM) is a free, community-maintained map of the world. Every road,
path, building and landmark is stored as either a **Node** (a lat/lon point) or a
**Way** (an ordered list of Node references).

The **Overpass API** is a read-only query interface to OSM. You send a query
describing what geographic objects you want, and it returns them as JSON or XML.

URL: `https://overpass-api.de/api/interpreter`

There is no API key. It is free and rate-limited by politeness — don't send more
than one heavy query every 60 seconds.

Alternative mirror if the main server is slow:
- `https://overpass.kumi.systems/api/interpreter`
- `https://overpass.openstreetmap.ru/api/interpreter`

---

## 0.2 What Data You Are Fetching

You will query two object types inside Vienna's bounding box:

```
Bounding box: south=48.118, west=16.183, north=48.324, east=16.578
```

| Query | What it gives you |
|-------|-------------------|
| `way["highway"]` inside bbox | Every named road, path, cycleway, steps, motorway segment |
| `node(w)` | All nodes referenced by those ways (junction points + shape points) |
| `way["railway"~"subway|light_rail|tram"]` inside bbox | Metro (U-Bahn) + tram lines |

A raw fetch of ALL `highway=*` in Vienna returns roughly:

| Object | Raw count | After curation |
|--------|-----------|----------------|
| Nodes | ~350 000 | ~1 000 |
| Ways | ~80 000 | ~3 000–5 000 |
| Edges (way segments) | ~200 000 | ~10 000 |

The raw data is ~80–120 MB of JSON. The curated subgraph is ~2–5 MB.

---

## 0.3 Curation Strategy — How to Get ~1 000 Nodes

You do **not** want 350 000 nodes — the algorithms would be too slow. The curation
pipeline keeps only high-value nodes by priority tier:

| Priority | What | Approx node count |
|----------|------|------------------|
| 1 | All intersections in 1st District (Innere Stadt) | ~200 |
| 2 | Major arteries: Ringstraße, Gürtel, Prater Hauptallee, Mariahilfer Str. | ~150 |
| 3 | Key Danube bridges: Reichsbrücke, Nordbrücke, Floridsdorfer Brücke, Stadionbrücke | ~60 |
| 4 | 8 tourist hotspot nodes + their 500m radius network | ~150 |
| 5 | U-Bahn station nodes (U1–U6, ~109 stations) | ~109 |
| 6 | Sampled residential roads from each of the 23 districts (5 nodes/district) | ~115 |
| 7 | Western hills: roads toward Wienerwald (for elevation/slope testing) | ~80 |
| **Total** | | **~850–1 000** |

After selecting nodes, keep all edges **between** selected nodes. Prune isolated
fragments (nodes with no edges to other selected nodes).

---

## 0.4 Overpass Query Structure

The script in Sprint 1 will send this query:

```
[out:json][timeout:180][bbox:48.118,16.183,48.324,16.578];
(
  way["highway"]["highway"!~"service|path|track|footway|steps|pedestrian|bridleway"]
    ["area"!="yes"];
  way["highway"~"footway|pedestrian|steps"]
    ["area"!="yes"];
  way["railway"~"subway|light_rail|tram"];
)->.ways;
node(w.ways)->.nodes;
(
  .ways;
  .nodes;
);
out body;
```

This deliberately includes footways and pedestrian paths (needed for the Walking
vehicle type) while excluding private service roads and tracks (not useful for
routing).

**Expected response size:** 30–80 MB JSON. The script saves it to
`data/vienna_raw.json` and then builds the curated subgraph.

---

## 0.5 Data Freshness and Caching

The OSM data is cached in `data/vienna_raw.json`. The curation step produces
`data/vienna_graph.json`. These files are gitignored.

If you run `scripts/fetch_osm_data.py` again, it will:
1. Check if `vienna_raw.json` already exists and is < 30 days old → skip the
   download and re-run curation only
2. If older or missing → re-download from Overpass

This means you only hit the Overpass server once per month, not on every run.

---

## 0.6 Edge Weight Model

Every edge in the graph stores:

```json
{
  "from": "node_id_A",
  "to": "node_id_B",
  "distance_m": 143.7,
  "road_type": "primary",
  "maxspeed": 50,
  "oneway": false,
  "name": "Mariahilfer Straße",
  "surface": "asphalt",
  "lit": "yes",
  "lanes": 3,
  "snow_priority": "A",
  "tram_track": false,
  "cycle_infra": "lane",
  "near_school": false,
  "near_green_space": true,
  "district": "6",
  "elevation_start_m": 180.2,
  "elevation_end_m": 181.0
}
```

The **raw edge weight for algorithm `g(n)`** is always `distance_m`. The heuristic
function `h(n)` returns a time-equivalent cost by multiplying `haversine_to_goal`
by the composite multiplier. This keeps g and h in the same unit (metres-equivalent
travel cost), ensuring admissibility holds under normal conditions.

---

---

# SPRINT 1 — Data Acquisition & Graph Construction

**Goal:** Run one Python script and produce `data/vienna_graph.json` with ~1 000
nodes and ~10 000 edges, ready for algorithm testing.

**Deliverable you can verify:** `python scripts/fetch_osm_data.py` completes
without errors and prints a summary table.

---

## Task 1.1 — Overpass Fetcher

**File:** `src/graph/osm_fetcher.py`

Implement the following:

```python
"""
OSM Overpass API fetcher.
Handles retries, mirrors, caching, and response validation.
"""
import json
import time
import hashlib
import os
from pathlib import Path
import requests

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

VIENNA_BBOX = (48.118, 16.183, 48.324, 16.578)  # south, west, north, east

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

    If cache_path exists and is younger than max_age_days, returns cached data.
    Otherwise downloads fresh data, saves it, and returns it.
    """
    if cache_path.exists():
        age_days = (time.time() - cache_path.stat().st_mtime) / 86400
        if age_days < max_age_days:
            print(f"[OSM] Using cached data ({age_days:.1f} days old): {cache_path}")
            with open(cache_path) as f:
                return json.load(f)

    query = OVERPASS_QUERY.format(
        south=VIENNA_BBOX[0], west=VIENNA_BBOX[1],
        north=VIENNA_BBOX[2], east=VIENNA_BBOX[3]
    )

    for i, mirror in enumerate(MIRRORS):
        try:
            print(f"[OSM] Fetching from mirror {i+1}/{len(MIRRORS)}: {mirror}")
            print("[OSM] This may take 30–90 seconds for Vienna...")
            resp = requests.post(mirror, data={"data": query}, timeout=200)
            resp.raise_for_status()
            data = resp.json()

            # Validate: we need both nodes and ways
            element_types = {e["type"] for e in data.get("elements", [])}
            assert "node" in element_types, "Response missing nodes"
            assert "way" in element_types, "Response missing ways"

            node_count = sum(1 for e in data["elements"] if e["type"] == "node")
            way_count = sum(1 for e in data["elements"] if e["type"] == "way")
            print(f"[OSM] Downloaded: {node_count:,} nodes, {way_count:,} ways")

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(data, f)
            print(f"[OSM] Saved to {cache_path} ({cache_path.stat().st_size / 1e6:.1f} MB)")
            return data

        except Exception as e:
            print(f"[OSM] Mirror {i+1} failed: {e}")
            if i < len(MIRRORS) - 1:
                time.sleep(5)

    raise RuntimeError("All Overpass mirrors failed. Check internet connection.")
```

---

## Task 1.2 — Graph Builder

**File:** `src/graph/builder.py`

This is the most complex script in Sprint 1. Implement in order:

### Step A — Parse raw OSM into node/way dicts

```python
def parse_osm(raw_data: dict) -> tuple[dict, list]:
    """
    Returns:
        nodes: dict of node_id -> {"lat": float, "lon": float, "tags": dict}
        ways:  list of {"id": int, "nodes": [id,...], "tags": dict}
    """
    nodes = {}
    ways = []
    for elem in raw_data["elements"]:
        if elem["type"] == "node":
            nodes[str(elem["id"])] = {
                "lat": elem["lat"],
                "lon": elem["lon"],
                "tags": elem.get("tags", {}),
            }
        elif elem["type"] == "way":
            ways.append({
                "id": elem["id"],
                "nodes": [str(n) for n in elem["nodes"]],
                "tags": elem.get("tags", {}),
            })
    return nodes, ways
```

### Step B — Haversine distance

```python
import math

def haversine(lat1, lon1, lat2, lon2) -> float:
    """Returns distance in metres between two lat/lon points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
```

### Step C — Tag enrichment

For each Way, derive the following fields from its OSM tags:

```python
ROAD_TYPE_DEFAULTS = {
    "motorway": 130, "trunk": 100, "primary": 50,
    "secondary": 50, "tertiary": 30, "residential": 30,
    "living_street": 10, "pedestrian": 5, "footway": 5,
    "cycleway": 20, "steps": 2, "subway": 80, "tram": 40,
    "light_rail": 80,
}

def enrich_way_tags(tags: dict) -> dict:
    """Convert raw OSM tags to structured edge metadata."""
    highway = tags.get("highway", tags.get("railway", "residential"))
    maxspeed_raw = tags.get("maxspeed", "")
    try:
        maxspeed = int(maxspeed_raw.split()[0]) if maxspeed_raw else ROAD_TYPE_DEFAULTS.get(highway, 30)
    except ValueError:
        maxspeed = ROAD_TYPE_DEFAULTS.get(highway, 30)

    oneway_val = tags.get("oneway", "no")
    oneway = oneway_val in ("yes", "1", "true")
    oneway_reverse = oneway_val == "-1"

    surface = tags.get("surface", "asphalt")
    if surface in ("paved", "concrete:plates"):
        surface = "asphalt"

    lanes_raw = tags.get("lanes", "")
    try:
        lanes = int(lanes_raw)
    except (ValueError, TypeError):
        lanes = 2 if highway in ("primary", "secondary", "trunk") else 1

    return {
        "road_type": highway,
        "maxspeed": maxspeed,
        "oneway": oneway,
        "oneway_reverse": oneway_reverse,
        "name": tags.get("name", ""),
        "surface": surface,
        "lit": tags.get("lit", "yes" if highway in ("primary", "secondary", "tertiary") else "unknown"),
        "lanes": lanes,
        "tram_track": tags.get("railway") == "tram" or tags.get("embedded_rails") == "yes",
        "cycle_infra": tags.get("cycleway", tags.get("cycleway:right", "none")),
        "bus_route": tags.get("bus") == "yes",
    }
```

### Step D — Derive district (1–23) from node coordinates

Vienna's 23 districts are concentric rings. Use a fast bounding-box lookup:

```python
# Approximate bounding boxes for Vienna districts 1–23
# Format: district_number -> (min_lat, min_lon, max_lat, max_lon)
DISTRICT_BOUNDS = {
    "1":  (48.198, 16.358, 48.220, 16.382),
    "2":  (48.195, 16.373, 48.248, 16.432),
    "3":  (48.183, 16.373, 48.212, 16.415),
    "4":  (48.182, 16.355, 48.202, 16.381),
    "5":  (48.183, 16.343, 48.203, 16.363),
    "6":  (48.190, 16.337, 48.207, 16.363),
    "7":  (48.196, 16.325, 48.213, 16.358),
    "8":  (48.203, 16.333, 48.221, 16.360),
    "9":  (48.218, 16.343, 48.240, 16.370),
    "10": (48.155, 16.336, 48.200, 16.392),
    "11": (48.162, 16.387, 48.215, 16.484),
    "12": (48.155, 16.292, 48.202, 16.360),
    "13": (48.143, 16.230, 48.208, 16.340),
    "14": (48.190, 16.262, 48.240, 16.345),
    "15": (48.183, 16.305, 48.218, 16.355),
    "16": (48.194, 16.297, 48.232, 16.355),
    "17": (48.217, 16.278, 48.267, 16.344),
    "18": (48.224, 16.310, 48.265, 16.365),
    "19": (48.225, 16.325, 48.295, 16.428),
    "20": (48.228, 16.358, 48.255, 16.403),
    "21": (48.246, 16.340, 48.325, 16.455),
    "22": (48.195, 16.420, 48.281, 16.578),
    "23": (48.118, 16.230, 48.183, 16.360),
}

def get_district(lat: float, lon: float) -> str:
    for district, (min_lat, min_lon, max_lat, max_lon) in DISTRICT_BOUNDS.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return district
    return "unknown"
```

### Step E — Node selection (curation)

```python
TOURIST_HOTSPOTS = [
    (48.2085, 16.3721),  # Stephansdom
    (48.1847, 16.3122),  # Schönbrunn
    (48.2066, 16.3644),  # Hofburg
    (48.1916, 16.3800),  # Belvedere
    (48.1980, 16.3719),  # Karlskirche
    (48.2165, 16.3955),  # Prater
    (48.1988, 16.3635),  # Naschmarkt
    (48.2100, 16.3570),  # Rathaus
]

UBAHN_STATIONS = [
    # A representative set of U-Bahn station coordinates.
    # Full list: https://data.wien.gv.at/daten/geo?service=WFS&...
    # You may also tag nodes where OSM has railway=station + network=*U-Bahn*
    (48.2093, 16.3736),  # Stephansplatz U1/U3
    (48.2100, 16.3710),  # Herrengasse U3
    (48.2000, 16.3880),  # Stadtpark U4
    (48.1850, 16.3130),  # Schönbrunn U4
    # ... Claude Code: fetch the full list from OSM at build time using
    # amenity=station + network=Wiener Linien tag filter on nodes
]

def select_nodes(nodes: dict, ways: list, target: int = 1000) -> set[str]:
    """
    Return a set of node IDs representing the curated subgraph.
    Prioritises: 1st district intersections, major arteries,
    bridges, tourist hotspots, U-Bahn stations, sampled residential.
    """
    selected = set()

    # Build adjacency to find intersections
    node_way_count: dict[str, int] = {}
    for way in ways:
        for nid in way["nodes"]:
            node_way_count[nid] = node_way_count.get(nid, 0) + 1

    for nid, node in nodes.items():
        lat, lon = node["lat"], node["lon"]
        district = get_district(lat, lon)

        # Priority 1: all intersections in 1st district
        if district == "1" and node_way_count.get(nid, 0) >= 2:
            selected.add(nid)

        # Priority 2: nodes on major named arteries
        # (handled below by way scanning)

        # Priority 4: within 600m of any tourist hotspot
        for (hlat, hlon) in TOURIST_HOTSPOTS:
            if haversine(lat, lon, hlat, hlon) < 600:
                selected.add(nid)
                break

    # Priority 2 & 3: scan ways for major roads and bridges
    MAJOR_ROAD_TYPES = {"motorway", "trunk", "primary"}
    BRIDGE_KEYWORDS = {"Brücke", "Bridge", "brücke", "Reichsbrücke", "Nordbrücke",
                       "Floridsdorfer", "Stadionbrücke", "Schwedenbrücke"}
    for way in ways:
        tags = way["tags"]
        road_type = tags.get("highway", tags.get("railway", ""))
        name = tags.get("name", "")
        is_bridge = tags.get("bridge") == "yes" or any(k in name for k in BRIDGE_KEYWORDS)
        is_major = road_type in MAJOR_ROAD_TYPES or tags.get("railway") in ("subway", "light_rail")

        if is_major or is_bridge:
            for nid in way["nodes"]:
                selected.add(nid)

    # Priority 5: U-Bahn station nodes (OSM: railway=station or railway=stop)
    for nid, node in nodes.items():
        ntags = node.get("tags", {})
        if ntags.get("railway") in ("station", "stop") and "Bahn" in ntags.get("network", ""):
            selected.add(nid)

    # Priority 6: sample residential nodes across all 23 districts
    per_district: dict[str, list[str]] = {}
    for nid, node in nodes.items():
        d = get_district(node["lat"], node["lon"])
        per_district.setdefault(d, []).append(nid)
    for d, nids in per_district.items():
        # take every Nth node to get ~10 per district
        step = max(1, len(nids) // 10)
        for nid in nids[::step]:
            selected.add(nid)

    print(f"[Builder] Selected {len(selected):,} nodes after curation")
    return selected
```

### Step F — Build final graph JSON

```python
def build_graph(nodes: dict, ways: list, selected_node_ids: set) -> dict:
    """
    Build the final adjacency-list graph from selected nodes only.
    """
    graph_nodes = {}
    for nid in selected_node_ids:
        if nid not in nodes:
            continue
        node = nodes[nid]
        graph_nodes[nid] = {
            "lat": node["lat"],
            "lon": node["lon"],
            "district": get_district(node["lat"], node["lon"]),
            "name": node.get("tags", {}).get("name", ""),
            "elevation_m": None,  # filled by precompute_elevation.py
        }

    edges = []
    adjacency: dict[str, list] = {nid: [] for nid in graph_nodes}

    for way in ways:
        enriched = enrich_way_tags(way["tags"])
        way_nodes = [n for n in way["nodes"] if n in graph_nodes]

        for i in range(len(way_nodes) - 1):
            n1, n2 = way_nodes[i], way_nodes[i + 1]
            if n1 == n2:
                continue
            lat1, lon1 = graph_nodes[n1]["lat"], graph_nodes[n1]["lon"]
            lat2, lon2 = graph_nodes[n2]["lat"], graph_nodes[n2]["lon"]
            dist = haversine(lat1, lon1, lat2, lon2)

            # Enrich edge with precomputed booleans
            near_school = any(
                haversine(lat1, lon1, slat, slon) < 200
                for slat, slon in SCHOOL_COORDS  # populated from OSM amenity=school
            )
            near_green = any(
                haversine(lat1, lon1, glat, glon) < 150
                for glat, glon in GREEN_SPACE_COORDS
            )

            edge = {
                **enriched,
                "from": n1,
                "to": n2,
                "distance_m": round(dist, 2),
                "near_school": near_school,
                "near_green_space": near_green,
                "snow_priority": "A" if enriched["road_type"] in
                    ("primary", "secondary", "trunk") or enriched["tram_track"] else "B",
            }
            edge_idx = len(edges)
            edges.append(edge)
            adjacency[n1].append({"node": n2, "edge_idx": edge_idx})

            # Reverse edge if not oneway
            if not enriched["oneway"]:
                rev_edge = {**edge, "from": n2, "to": n1}
                rev_idx = len(edges)
                edges.append(rev_edge)
                adjacency[n2].append({"node": n1, "edge_idx": rev_idx})
            elif enriched["oneway_reverse"]:
                rev_edge = {**edge, "from": n2, "to": n1}
                rev_idx = len(edges)
                edges.append(rev_edge)
                adjacency[n2].append({"node": n1, "edge_idx": rev_idx})

    # Prune isolated nodes (no edges)
    connected = {n for n, adj in adjacency.items() if adj}
    graph_nodes = {n: v for n, v in graph_nodes.items() if n in connected}
    adjacency = {n: v for n, v in adjacency.items() if n in connected}

    return {
        "nodes": graph_nodes,
        "edges": edges,
        "adjacency": adjacency,
        "meta": {
            "node_count": len(graph_nodes),
            "edge_count": len(edges),
            "bbox": VIENNA_BBOX,
        }
    }
```

---

## Task 1.3 — Fetch Script

**File:** `scripts/fetch_osm_data.py`

```python
#!/usr/bin/env python3
"""
One-time script to download Vienna OSM data and build the curated graph.
Run: python scripts/fetch_osm_data.py

Output:
  data/vienna_raw.json     (~30-80 MB, cached 30 days)
  data/vienna_graph.json   (~2-5 MB, the graph your app uses)
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.osm_fetcher import fetch_vienna_osm
from src.graph.builder import parse_osm, select_nodes, build_graph

RAW_PATH = Path("data/vienna_raw.json")
GRAPH_PATH = Path("data/vienna_graph.json")

def main():
    print("=" * 60)
    print("Vienna Traffic Router — Graph Builder")
    print("=" * 60)

    # Step 1: Fetch raw OSM data
    raw = fetch_vienna_osm(RAW_PATH)

    # Step 2: Parse
    print("[Builder] Parsing OSM elements...")
    nodes, ways = parse_osm(raw)
    print(f"[Builder] Parsed {len(nodes):,} nodes, {len(ways):,} ways")

    # Step 3: Curate
    selected = select_nodes(nodes, ways)

    # Step 4: Build graph
    print("[Builder] Building graph...")
    graph = build_graph(nodes, ways, selected)

    # Step 5: Save
    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f)

    print()
    print("=" * 60)
    print("Graph build complete!")
    print(f"  Nodes:  {graph['meta']['node_count']:>8,}")
    print(f"  Edges:  {graph['meta']['edge_count']:>8,}")
    print(f"  Size:   {GRAPH_PATH.stat().st_size / 1e6:.2f} MB")
    print(f"  Saved:  {GRAPH_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
python scripts/fetch_osm_data.py
```

**Expected output:**
```
[OSM] Fetching from mirror 1/3: https://overpass-api.de/api/interpreter
[OSM] This may take 30–90 seconds for Vienna...
[OSM] Downloaded: 312,444 nodes, 74,821 ways
[OSM] Saved to data/vienna_raw.json (67.3 MB)
[Builder] Parsing 312,444 nodes, 74,821 ways
[Builder] Selected 987 nodes after curation
[Builder] Building graph...
Graph build complete!
  Nodes:        987
  Edges:      9,841
  Size:   3.24 MB
  Saved:  data/vienna_graph.json
```

> **Checkpoint 1 done.** Open `data/vienna_graph.json` in any editor. Verify you
> see node entries with lat/lon and edge entries with distance_m. Spot-check: node
> near `48.2082, 16.3738` should be Stephansplatz area.

---

---

# SPRINT 2 — Search Algorithms

**Goal:** Implement all 8 search algorithms and a runner that executes them all in
parallel. Verify with a hardcoded test pair.

**Deliverable:** `python -c "from src.algorithms.runner import run_all; print(run_all('NODE_A', 'NODE_B', {}))"` returns a dict with 8 results.

---

## Task 2.1 — Base Types

**File:** `src/algorithms/base.py`

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PathResult:
    algorithm: str
    path_node_ids: list[str]
    path_coords: list[tuple[float, float]]   # [(lat, lon), ...]
    distance_m: float
    estimated_time_s: float
    nodes_expanded: int
    compute_time_ms: float
    is_optimal: Optional[bool] = None
    optimality_gap_pct: Optional[float] = None
    error: Optional[str] = None
```

---

## Task 2.2 — Graph Loader

**File:** `src/graph/loader.py`

```python
import json
from pathlib import Path
from functools import lru_cache

_GRAPH = None

def load_graph(path: str = "data/vienna_graph.json") -> dict:
    global _GRAPH
    if _GRAPH is None:
        with open(path) as f:
            _GRAPH = json.load(f)
    return _GRAPH

def get_node(graph: dict, node_id: str) -> dict:
    return graph["nodes"][node_id]

def get_neighbors(graph: dict, node_id: str) -> list[dict]:
    """Returns list of {node, edge_idx} dicts."""
    return graph["adjacency"].get(node_id, [])

def get_edge(graph: dict, edge_idx: int) -> dict:
    return graph["edges"][edge_idx]

def get_edge_cost(graph: dict, edge_idx: int) -> float:
    """Raw g(n) cost = distance in metres."""
    return graph["edges"][edge_idx]["distance_m"]

def nearest_node(graph: dict, lat: float, lon: float) -> str:
    """Find the graph node closest to a lat/lon coordinate."""
    from src.graph.builder import haversine
    best_id, best_dist = None, float("inf")
    for nid, node in graph["nodes"].items():
        d = haversine(lat, lon, node["lat"], node["lon"])
        if d < best_dist:
            best_dist = d
            best_id = nid
    return best_id
```

---

## Task 2.3 — Uninformed Algorithms

Each algorithm file follows the same interface:
```python
def find_path(graph, start_id, goal_id, heuristic_fn, params) -> PathResult
```

### BFS — `src/algorithms/bfs.py`

```python
import time
from collections import deque
from .base import PathResult
from src.graph.loader import get_neighbors, get_edge_cost, get_node

def find_path(graph, start_id, goal_id, heuristic_fn, params) -> PathResult:
    t0 = time.perf_counter()
    queue = deque([[start_id]])
    visited = {start_id}
    nodes_expanded = 0

    while queue:
        path = queue.popleft()
        current = path[-1]
        nodes_expanded += 1

        if current == goal_id:
            coords = [(graph["nodes"][n]["lat"], graph["nodes"][n]["lon"]) for n in path]
            dist = sum(
                get_edge_cost(graph, nb["edge_idx"])
                for i, node in enumerate(path[:-1])
                for nb in get_neighbors(graph, node)
                if nb["node"] == path[i + 1]
            )
            return PathResult(
                algorithm="bfs", path_node_ids=path, path_coords=coords,
                distance_m=dist, estimated_time_s=dist / 8.33,
                nodes_expanded=nodes_expanded,
                compute_time_ms=(time.perf_counter() - t0) * 1000,
            )

        for nb in get_neighbors(graph, current):
            nid = nb["node"]
            if nid not in visited:
                visited.add(nid)
                queue.append(path + [nid])

    return PathResult(
        algorithm="bfs", path_node_ids=[], path_coords=[], distance_m=-1,
        estimated_time_s=-1, nodes_expanded=nodes_expanded,
        compute_time_ms=(time.perf_counter() - t0) * 1000,
        error="No path found",
    )
```

### DFS — `src/algorithms/dfs.py`

Same structure as BFS but use a stack (`list` with `.pop()`). Add a depth limit of
`len(graph["nodes"]) * 2` to prevent infinite loops on large graphs.

### UCS — `src/algorithms/ucs.py`

Use `heapq`. Priority = cumulative distance `g(n)`. This is Dijkstra without the
visited-node relaxation check — it will reopen nodes if a cheaper path is found.

### Dijkstra — `src/algorithms/dijkstra.py`

```python
import heapq, time
from .base import PathResult
from src.graph.loader import get_neighbors, get_edge_cost

def find_path(graph, start_id, goal_id, heuristic_fn, params) -> PathResult:
    t0 = time.perf_counter()
    dist = {start_id: 0.0}
    prev = {start_id: None}
    heap = [(0.0, start_id)]
    visited = set()
    nodes_expanded = 0

    while heap:
        g, current = heapq.heappop(heap)
        if current in visited:
            continue
        visited.add(current)
        nodes_expanded += 1

        if current == goal_id:
            # Reconstruct path
            path = []
            node = goal_id
            while node is not None:
                path.append(node)
                node = prev[node]
            path.reverse()
            coords = [(graph["nodes"][n]["lat"], graph["nodes"][n]["lon"]) for n in path]
            return PathResult(
                algorithm="dijkstra", path_node_ids=path, path_coords=coords,
                distance_m=dist[goal_id], estimated_time_s=dist[goal_id] / 8.33,
                nodes_expanded=nodes_expanded,
                compute_time_ms=(time.perf_counter() - t0) * 1000,
            )

        for nb in get_neighbors(graph, current):
            nid = nb["node"]
            if nid in visited:
                continue
            new_dist = g + get_edge_cost(graph, nb["edge_idx"])
            if new_dist < dist.get(nid, float("inf")):
                dist[nid] = new_dist
                prev[nid] = current
                heapq.heappush(heap, (new_dist, nid))

    return PathResult(algorithm="dijkstra", path_node_ids=[], path_coords=[],
                      distance_m=-1, estimated_time_s=-1, nodes_expanded=nodes_expanded,
                      compute_time_ms=(time.perf_counter() - t0) * 1000, error="No path")
```

---

## Task 2.4 — Informed Algorithms

### Greedy Best-First — `src/algorithms/greedy_best_first.py`

Like A\* but priority = `h(n)` only (no `g(n)`). Uses `heapq`. Call
`heuristic_fn(node_id, goal_id, graph, params)` for the heuristic value.

### A\* — `src/algorithms/astar.py`

Priority = `g(n) + h(n)`. Otherwise identical structure to Dijkstra.
Pass `heuristic_fn` and `params` through.

### Weighted A\* — `src/algorithms/weighted_astar.py`

Priority = `g(n) + w * h(n)`. Read `w = params.get("w", 1.5)`.

### Bidirectional A\* — `src/algorithms/bidirectional_astar.py`

Run forward A\* from start and backward A\* from goal simultaneously. After each
expansion, check if the two frontiers have met. The meeting node gives the path.
This is the most complex algorithm — implement it last.

**Simplified version for meeting condition:**
```
At each step, expand the frontier with lower f-value.
Stop when any node appears in BOTH closed sets.
Reconstruct path by joining the two partial paths at the meeting node.
```

---

## Task 2.5 — Base Heuristic

**File:** `src/heuristics/combined.py` (stub for now)

```python
from src.graph.builder import haversine

def base_heuristic(node_id: str, goal_id: str, graph: dict, params: dict) -> float:
    """
    Admissible base heuristic: straight-line Haversine distance to goal.
    Returns distance in metres (same unit as edge weights).
    """
    node = graph["nodes"][node_id]
    goal = graph["nodes"][goal_id]
    return haversine(node["lat"], node["lon"], goal["lat"], goal["lon"])
```

---

## Task 2.6 — Runner

**File:** `src/algorithms/runner.py`

```python
"""
Runs all 8 algorithms in parallel and returns a unified comparison result.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.algorithms import bfs, dfs, ucs, dijkstra
from src.algorithms import greedy_best_first, astar, weighted_astar, bidirectional_astar
from src.graph.loader import load_graph, nearest_node
from src.heuristics.combined import base_heuristic

ALGORITHMS = {
    "bfs": bfs,
    "dfs": dfs,
    "ucs": ucs,
    "dijkstra": dijkstra,
    "greedy": greedy_best_first,
    "astar": astar,
    "weighted_astar": weighted_astar,
    "bidirectional_astar": bidirectional_astar,
}

def run_all(start_lat: float, start_lon: float, goal_lat: float, goal_lon: float,
            params: dict, heuristic_fn=None) -> dict:
    """
    Find path for all 8 algorithms between two lat/lon points.
    Returns unified comparison dict.
    """
    if heuristic_fn is None:
        heuristic_fn = base_heuristic

    graph = load_graph()
    start_id = nearest_node(graph, start_lat, start_lon)
    goal_id = nearest_node(graph, goal_lat, goal_lon)

    t_total = time.perf_counter()
    results = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(algo.find_path, graph, start_id, goal_id, heuristic_fn, params): name
            for name, algo in ALGORITHMS.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                from src.algorithms.base import PathResult
                results[name] = PathResult(
                    algorithm=name, path_node_ids=[], path_coords=[],
                    distance_m=-1, estimated_time_s=-1, nodes_expanded=0,
                    compute_time_ms=0, error=str(e),
                )

    total_ms = (time.perf_counter() - t_total) * 1000

    # Compute optimality: Dijkstra is ground truth
    optimal_dist = results["dijkstra"].distance_m
    for r in results.values():
        if r.distance_m > 0 and optimal_dist > 0:
            r.is_optimal = abs(r.distance_m - optimal_dist) < 1.0
            r.optimality_gap_pct = round((r.distance_m - optimal_dist) / optimal_dist * 100, 1)

    return {
        "start_node": start_id,
        "goal_node": goal_id,
        "start_coords": [start_lat, start_lon],
        "goal_coords": [goal_lat, goal_lon],
        "results": {name: vars(r) for name, r in results.items()},
        "optimal_distance_m": optimal_dist,
        "total_compute_time_ms": round(total_ms, 1),
    }
```

> **Checkpoint 2 done.** Test with:
> ```python
> from src.algorithms.runner import run_all
> r = run_all(48.2082, 16.3738, 48.1847, 16.3122, {})
> for name, res in r["results"].items():
>     print(f"{name:25s} {res['distance_m']:.0f}m  nodes={res['nodes_expanded']}")
> ```
> You should see 8 rows. Dijkstra and A\* should have the same distance.
> BFS and DFS will be longer. DFS may be very long.

---

---

# SPRINT 3 — FastAPI Backend

**Goal:** Expose the algorithms through HTTP endpoints. A browser can call
`POST /api/find-path` and get back 8 routes.

**Deliverable:** `uvicorn src.main:app --reload` starts. `curl` to `/api/find-path`
returns a 200 response with routes.

---

## Task 3.1 — FastAPI App

**File:** `src/main.py`

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from src.routes.api import router

app = FastAPI(title="Vienna Traffic Router", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.mount("/", StaticFiles(directory="public", html=True), name="static")
```

---

## Task 3.2 — Request/Response Models

**File:** `src/routes/api.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx, os

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
    route_profile: str = "fastest"  # fastest | safest | greenest
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

# In-memory store for manual overrides
_overrides: dict[str, int] = {}

@router.post("/find-path")
async def find_path(req: FindPathRequest):
    from src.algorithms.runner import run_all
    from src.heuristics.combined import make_heuristic

    params = req.dict()
    params["manual_overrides"] = _overrides  # inject stored overrides

    heuristic_fn = make_heuristic(params)
    result = run_all(
        req.start_lat, req.start_lon,
        req.goal_lat, req.goal_lon,
        params, heuristic_fn,
    )
    return result

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
    if not api_key:
        return {"error": "No API key", "weather": "clear", "temp": 15,
                "humidity": 60, "wind_speed": 3, "wind_deg": 180, "visibility": 5000}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": "Vienna,AT", "appid": api_key, "units": "metric"},
            timeout=10,
        )
        data = resp.json()
    weather_id = data["weather"][0]["id"]
    # Map OWM weather IDs to internal codes
    if weather_id >= 600:    condition = "snow"
    elif weather_id >= 500:  condition = "rain"
    elif weather_id >= 300:  condition = "light_rain"
    elif weather_id >= 200:  condition = "thunderstorm"
    elif weather_id == 741:  condition = "fog"
    else:                    condition = "clear"

    return {
        "weather": condition,
        "temp": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "wind_speed": data["wind"]["speed"],
        "wind_deg": data["wind"].get("deg", 0),
        "visibility": data.get("visibility", 5000),
        "description": data["weather"][0]["description"],
    }

@router.get("/graph/stats")
async def graph_stats():
    from src.graph.loader import load_graph
    g = load_graph()
    return g["meta"]

@router.get("/events/{date}")
async def get_events(date: str):
    from src.heuristics.events import get_active_events
    return {"events": get_active_events(date)}
```

**Run:**
```bash
uvicorn src.main:app --reload --port 8000
```

Visit `http://localhost:8000/api/graph/stats` — you should see node count and edge count.

> **Checkpoint 3 done.** Test the find-path endpoint:
> ```bash
> curl -X POST http://localhost:8000/api/find-path \
>   -H "Content-Type: application/json" \
>   -d '{"start_lat":48.2082,"start_lon":16.3738,"goal_lat":48.1847,"goal_lon":16.3122}'
> ```
> You should receive a JSON body with `results` containing 8 algorithm entries.

---

---

# SPRINT 4 — Core Heuristics

**Goal:** Implement the heuristic engine. The `make_heuristic` factory builds a
composite heuristic function from all active parameters.

**Deliverable:** Re-run the same path request with `vehicle_type=bicycle` and
`weather=heavy_rain` — the routes should change compared to the baseline.

---

## Task 4.1 — Weather Heuristic

**File:** `src/heuristics/weather.py`

```python
WEATHER_MULTIPLIERS = {
    "clear":       1.0,
    "cloudy":      1.1,
    "light_rain":  1.25,
    "rain":        1.5,
    "heavy_rain":  1.5,
    "thunderstorm":1.6,
    "fog":         1.3,
    "light_snow":  1.4,
    "snow":        1.6,
    "heavy_snow":  1.8,
    "black_ice":   2.0,
}

def get_weather_multiplier(weather: str) -> float:
    return WEATHER_MULTIPLIERS.get(weather, 1.0)

def infer_black_ice(temp: float, humidity: float, weather: str) -> str:
    """Infer black ice risk from temperature + humidity."""
    if temp < 2 and humidity > 80 and weather in ("clear", "cloudy", "fog"):
        return "black_ice"
    return weather
```

---

## Task 4.2 — Time of Day Heuristic

**File:** `src/heuristics/time_of_day.py`

```python
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
```

---

## Task 4.3 — Vehicle Type Heuristic

**File:** `src/heuristics/vehicle_type.py`

```python
VEHICLE_MULTIPLIERS = {
    "car":        1.0,
    "motorcycle": 0.85,
    "taxi":       1.05,
    "bus":        1.30,
    "metro":      0.40,
    "train":      0.45,
    "walking":    1.80,
    "bicycle":    1.20,
    "truck":      1.60,
    "escooter":   1.30,
}

# Edge road types this vehicle can NOT use
FORBIDDEN_ROAD_TYPES = {
    "metro":    lambda rt: rt not in ("subway", "light_rail"),
    "train":    lambda rt: rt not in ("rail", "light_rail"),
    "walking":  lambda rt: rt in ("motorway", "trunk"),
    "bicycle":  lambda rt: rt in ("motorway", "trunk"),
    "escooter": lambda rt: rt in ("motorway", "trunk", "steps"),
    "bus":      lambda rt: rt in ("cycleway", "footway", "steps", "pedestrian"),
}

def is_forbidden_for_vehicle(road_type: str, vehicle: str) -> bool:
    check = FORBIDDEN_ROAD_TYPES.get(vehicle)
    return check(road_type) if check else False

def get_vehicle_multiplier(vehicle: str) -> float:
    return VEHICLE_MULTIPLIERS.get(vehicle, 1.0)
```

---

## Task 4.4 — Combined Heuristic Factory

**File:** `src/heuristics/combined.py`

```python
"""
The combined heuristic factory.
make_heuristic(params) returns a callable h(node_id, goal_id, graph, params).
Each active heuristic contributes a multiplier. The product is clamped.
"""
import math
from src.graph.builder import haversine
from src.heuristics.weather import get_weather_multiplier, infer_black_ice
from src.heuristics.time_of_day import get_time_multiplier
from src.heuristics.vehicle_type import get_vehicle_multiplier, is_forbidden_for_vehicle
# ... import all other heuristics as you implement them in Sprint 5

MAX_HEURISTIC_CAP = 50.0  # metres * this cap = maximum h value

def make_heuristic(params: dict):
    """
    Returns a heuristic function tuned to the given params.
    The returned function signature: h(node_id, goal_id, graph) -> float
    """
    weather = infer_black_ice(params["temperature"], params["humidity"], params["weather"])
    enabled = set(params.get("enabled_heuristics", []))

    # Pre-compute static multipliers (not edge-dependent)
    w_weather = get_weather_multiplier(weather) if "weather" not in enabled or True else 1.0
    w_time    = get_time_multiplier(params["hour"], params["day_of_week"])
    w_vehicle = get_vehicle_multiplier(params["vehicle_type"])
    static_mult = w_weather * w_time * w_vehicle

    def heuristic(node_id: str, goal_id: str, graph: dict, _params: dict = None) -> float:
        node = graph["nodes"][node_id]
        goal = graph["nodes"][goal_id]
        h_base = haversine(node["lat"], node["lon"], goal["lat"], goal["lon"])

        # Edge-dependent multipliers will be added in Sprint 5
        # For now: static only
        h = h_base * static_mult

        return min(h, MAX_HEURISTIC_CAP * h_base)

    return heuristic


# Legacy single-call entry point used by algorithms directly
def base_heuristic(node_id: str, goal_id: str, graph: dict, params: dict) -> float:
    node = graph["nodes"][node_id]
    goal = graph["nodes"][goal_id]
    return haversine(node["lat"], node["lon"], goal["lat"], goal["lon"])
```

---

> **Checkpoint 4 done.** Call `/api/find-path` with `weather=heavy_snow` and
> `vehicle_type=bicycle`. Compare to `weather=clear` / `vehicle_type=car`.
> The time estimates should differ noticeably.

---

---

# SPRINT 5 — Vienna-Specific Heuristics

**Goal:** Implement all 22 Vienna-specific heuristic modules and wire them into
`combined.py`. Each is a separate file. Implement them **one at a time** and test
each by toggling it on/off in a route request.

The list below is the implementation order (easiest → most complex). For each,
the file path, the key lookup table, and the function signature are provided.
Full implementation details are in the heuristics reference section at the end
of this document.

| # | File | Key data source | When active |
|---|------|----------------|-------------|
| 1 | `intersection_density.py` | Node degree + `highway=traffic_signals` | Always |
| 2 | `surface.py` | Edge `surface` tag | Always |
| 3 | `elevation.py` | Edge `elevation_start/end_m` | Walking, cycling, bus |
| 4 | `safety.py` | Edge `lit` tag + road class | Walking, 21:00–05:00 |
| 5 | `emission_zones.py` | Edge `motor_vehicle=no` tag | Car, truck |
| 6 | `headway.py` | Line frequency tables | Metro, train |
| 7 | `tram_tracks.py` | Edge `tram_track` boolean | Bicycle |
| 8 | `wind.py` | OWM wind_speed + wind_deg | Bicycle, walking |
| 9 | `parking.py` | District parking table | Car (goal node) |
| 10 | `scenic.py` | Edge `near_green_space` bool | Greenest profile |
| 11 | `school_zones.py` | Edge `near_school` bool | 07:30–08:15, 13:00–14:00 |
| 12 | `holiday_historical.py` | Date + hotspot proximity | Holidays |
| 13 | `events.py` | `data/events_2026.json` | Event dates/hours |
| 14 | `fiaker.py` | District "1" + tourist hours | Car, bicycle, 10:00–18:00 |
| 15 | `snow_priority.py` | Edge `snow_priority` tag | Snow weather |
| 16 | `commuter_bridges.py` | Bridge name lookup | Rush hours, weekdays |
| 17 | `markets.py` | Market coordinate table | Saturday mornings |
| 18 | `heuriger.py` | Heuriger zone table | Sep–Oct, Fri–Sat evenings |
| 19 | `season.py` | Month → season | Always |
| 20 | `lane_capacity.py` | Edge `lanes` tag | Car, bus |
| 21 | `road_works.py` | `data/road_works_2026.json` | Active dates |
| 22 | `pedestrian_density.py` | Zone + hour + is_holiday | Car, bicycle |

**After implementing each module**, add it to `combined.py`:
```python
from src.heuristics.school_zones import get_school_multiplier
# ... and call it inside the heuristic() closure
```

> **Checkpoint 5 done.** Enable all 22 heuristics and run:
> - Car, 08:00 Mon, clear → should prefer Gürtel over 1st district bridges
> - Bicycle, 08:00 Mon, heavy rain → should avoid tram tracks
> - Walking, 02:00, any → should prefer lit primary roads

---

---

# SPRINT 6 — Frontend (Beautiful Dark UI)

**Goal:** Build a complete, beautiful web interface. This is the most visual sprint.
Work on it section by section. The UI is described in detail below.

**Deliverable:** Open `http://localhost:8000`. The map loads, you click two points,
and all 8 routes appear on the map with the comparison table below.

---

## Design Language

**Theme:** Imperial Vienna, after dark. Deep midnight blues and charcoal grays as
base. Warm gold (#C9A84C) as the single accent colour — echoing the gilded
architecture of the Ringstraße. Monospaced numbers in the data table, refined
serif (`Playfair Display`) for place names, clean sans (`DM Sans`) for UI labels.

**Palette:**
```css
--bg-deep:       #0d1117;   /* map backdrop, deepest panels */
--bg-panel:      #161b22;   /* sidebar, drawer */
--bg-surface:    #1c2128;   /* card, input backgrounds */
--bg-hover:      #22272e;   /* hover states */
--border:        #30363d;   /* all borders */
--text-primary:  #e6edf3;   /* main text */
--text-muted:    #8b949e;   /* labels, secondary */
--accent:        #C9A84C;   /* gold: CTAs, active states, selection */
--accent-dim:    #8a6f30;   /* dimmed gold for backgrounds */
--green:         #3fb950;   /* optimal route, ✓ OPT badge */
--amber:         #d29922;   /* 1–10% gap */
--red:           #f85149;   /* >10% gap */
--route-colors: [
    "#C9A84C",  /* Dijkstra — gold */
    "#3fb950",  /* A* — green */
    "#58a6ff",  /* Weighted A* — blue */
    "#79c0ff",  /* Bidirectional A* — light blue */
    "#f78166",  /* Greedy — salmon */
    "#a5d6ff",  /* UCS — pale blue */
    "#d2a8ff",  /* BFS — lavender */
    "#ffa657",  /* DFS — orange */
];
```

**Typography:**
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
```

```css
--font-display:  'Playfair Display', Georgia, serif;
--font-ui:       'DM Sans', system-ui, sans-serif;
--font-mono:     'DM Mono', 'Fira Code', monospace;
```

---

## Task 6.1 — HTML Structure

**File:** `public/index.html`

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vienna Traffic Router</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🗺️</text></svg>">

  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">

  <!-- Leaflet -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <!-- App styles -->
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>

  <!-- TOP BAR -->
  <header id="topbar">
    <div class="topbar-left">
      <span class="app-logo">🗺️</span>
      <span class="app-title">Vienna Traffic Router</span>
    </div>
    <div class="topbar-center">
      <button id="weather-badge" class="weather-badge" title="Click to refresh weather">
        <span id="weather-icon">☀️</span>
        <span id="weather-temp">—°C</span>
        <span id="weather-desc" class="muted">loading…</span>
      </button>
    </div>
    <div class="topbar-right">
      <span class="mode-label muted">Mode</span>
      <label class="mode-toggle">
        <input type="checkbox" id="advanced-toggle">
        <span class="toggle-track">
          <span class="toggle-label-left">Simple</span>
          <span class="toggle-thumb"></span>
          <span class="toggle-label-right">Advanced</span>
        </span>
      </label>
      <span id="heuristic-count-badge" class="heuristic-badge" title="Active heuristics">
        <span id="heuristic-count">0</span> heuristics
      </span>
    </div>
  </header>

  <!-- MAIN LAYOUT -->
  <main id="app-layout">

    <!-- LEFT SIDEBAR -->
    <aside id="sidebar" class="sidebar">
      <div id="sidebar-inner">

        <!-- ORIGIN / DESTINATION -->
        <section class="panel" id="panel-location">
          <label class="field-label">
            <span class="pin pin-start">A</span> Origin
          </label>
          <div class="location-input-wrap">
            <input type="text" id="input-start" class="location-input"
              placeholder="Click map or search…" autocomplete="off">
            <button class="btn-locate" id="btn-locate" title="Use my location">📍</button>
          </div>
          <div id="start-coords" class="coord-display muted"></div>

          <label class="field-label" style="margin-top:12px">
            <span class="pin pin-goal">B</span> Destination
          </label>
          <div class="location-input-wrap">
            <input type="text" id="input-goal" class="location-input"
              placeholder="Click map or type address…" autocomplete="off">
          </div>
          <div id="goal-coords" class="coord-display muted"></div>
        </section>

        <!-- VEHICLE -->
        <section class="panel" id="panel-vehicle">
          <div class="panel-header">Vehicle</div>
          <div class="vehicle-grid" id="vehicle-selector">
            <button class="vehicle-btn active" data-vehicle="car"        title="Car">🚗</button>
            <button class="vehicle-btn" data-vehicle="motorcycle"         title="Motorcycle">🏍️</button>
            <button class="vehicle-btn" data-vehicle="taxi"               title="Taxi">🚕</button>
            <button class="vehicle-btn" data-vehicle="bicycle"            title="Bicycle">🚴</button>
            <button class="vehicle-btn" data-vehicle="escooter"           title="E-Scooter">🛴</button>
            <button class="vehicle-btn" data-vehicle="walking"            title="Walking">🚶</button>
            <button class="vehicle-btn" data-vehicle="bus"                title="Bus">🚌</button>
            <button class="vehicle-btn" data-vehicle="metro"              title="Metro (U-Bahn)">🚇</button>
            <button class="vehicle-btn" data-vehicle="train"              title="S-Bahn">🚂</button>
            <button class="vehicle-btn" data-vehicle="truck"              title="HGV / Truck">🚛</button>
          </div>
        </section>

        <!-- ROUTE PROFILE -->
        <section class="panel" id="panel-profile">
          <div class="panel-header">Route Profile</div>
          <div class="profile-tabs" id="profile-selector">
            <button class="profile-tab active" data-profile="fastest">
              <span class="profile-icon">⚡</span>
              <span>Fastest</span>
            </button>
            <button class="profile-tab" data-profile="safest">
              <span class="profile-icon">🛡️</span>
              <span>Safest</span>
            </button>
            <button class="profile-tab" data-profile="greenest">
              <span class="profile-icon">🌿</span>
              <span>Greenest</span>
            </button>
          </div>
        </section>

        <!-- DATE & TIME -->
        <section class="panel" id="panel-time">
          <div class="panel-header">
            Date & Time
            <label class="inline-toggle" title="Use current time">
              <input type="checkbox" id="use-current-time" checked>
              <span>Now</span>
            </label>
          </div>
          <div class="time-row">
            <input type="date" id="input-date" class="input-field">
            <input type="time" id="input-time" class="input-field" step="900">
          </div>
          <div class="time-slider-wrap">
            <span class="muted small">0h</span>
            <input type="range" id="hour-slider" min="0" max="23" value="12" class="hour-slider">
            <span class="muted small">23h</span>
          </div>
          <div id="time-label" class="time-label-display">12:00 · Weekday</div>
        </section>

        <!-- ADVANCED: CONDITIONS (hidden in simple mode) -->
        <section class="panel advanced-only" id="panel-conditions">
          <div class="panel-header collapsible" data-target="conditions-body">
            ⛅ Conditions
            <span class="chevron">›</span>
          </div>
          <div id="conditions-body" class="panel-body">
            <div class="field-label">Weather</div>
            <div class="weather-grid" id="weather-selector">
              <button class="weather-btn active" data-weather="clear">☀️<br><small>Clear</small></button>
              <button class="weather-btn" data-weather="cloudy">⛅<br><small>Cloudy</small></button>
              <button class="weather-btn" data-weather="fog">🌫️<br><small>Fog</small></button>
              <button class="weather-btn" data-weather="light_rain">🌦️<br><small>Light Rain</small></button>
              <button class="weather-btn" data-weather="rain">🌧️<br><small>Rain</small></button>
              <button class="weather-btn" data-weather="thunderstorm">⛈️<br><small>Storm</small></button>
              <button class="weather-btn" data-weather="light_snow">🌨️<br><small>Light Snow</small></button>
              <button class="weather-btn" data-weather="heavy_snow">❄️<br><small>Blizzard</small></button>
            </div>
            <button id="auto-weather-btn" class="btn-secondary small">🔄 Auto-detect from API</button>

            <div class="slider-row">
              <label>Temperature</label>
              <input type="range" id="temp-slider" min="-15" max="40" value="15" class="param-slider">
              <span class="slider-val" id="temp-val">15°C</span>
            </div>
            <div class="slider-row">
              <label>Humidity</label>
              <input type="range" id="humidity-slider" min="0" max="100" value="60" class="param-slider">
              <span class="slider-val" id="humidity-val">60%</span>
            </div>
            <div class="slider-row">
              <label>Visibility</label>
              <input type="range" id="visibility-slider" min="50" max="5000" step="50" value="5000" class="param-slider">
              <span class="slider-val" id="visibility-val">5.0 km</span>
            </div>
            <div class="slider-row">
              <label>Wind speed</label>
              <input type="range" id="wind-slider" min="0" max="30" value="3" class="param-slider">
              <span class="slider-val" id="wind-val">3 m/s <span id="wind-dir">↗</span></span>
            </div>
          </div>
        </section>

        <!-- ADVANCED: HEURISTICS (hidden in simple mode) -->
        <section class="panel advanced-only" id="panel-heuristics">
          <div class="panel-header collapsible" data-target="heuristics-body">
            ⚙️ Heuristics
            <span class="heuristic-sub-count" id="heuristic-sub-count">0 / 22 active</span>
            <span class="chevron">›</span>
          </div>
          <div id="heuristics-body" class="panel-body">
            <div class="heuristic-actions">
              <button class="btn-ghost small" id="btn-enable-all">Enable All</button>
              <button class="btn-ghost small" id="btn-disable-all">Disable All</button>
            </div>
            <div id="heuristic-list" class="heuristic-list">
              <!-- Generated by sidebar.js from HEURISTICS_METADATA -->
            </div>

            <!-- Live weight breakdown -->
            <div class="weight-breakdown" id="weight-breakdown">
              <div class="panel-header small">Live Weight Breakdown</div>
              <div id="weight-bars"></div>
              <div class="composite-row">
                Composite multiplier: <strong id="composite-mult">×1.0</strong>
              </div>
            </div>
          </div>
        </section>

        <!-- ADVANCED: MANUAL OVERRIDE -->
        <section class="panel advanced-only" id="panel-override">
          <div class="panel-header collapsible" data-target="override-body">
            🛣️ Manual Road Override
            <span class="chevron">›</span>
          </div>
          <div id="override-body" class="panel-body">
            <p class="muted small">Click any road segment on the map to select it.</p>
            <div id="override-selected" class="override-selected hidden">
              <div id="override-road-name" class="override-road-name">—</div>
              <div class="override-road-meta" id="override-road-meta"></div>
              <div class="slider-row">
                <span class="small muted">🟢 Free</span>
                <input type="range" id="override-slider" min="0" max="100" value="50" class="param-slider">
                <span class="small muted">🔴 Jam</span>
              </div>
              <div class="override-val-display" id="override-val-display">50% — Normal</div>
              <div class="override-actions">
                <button class="btn-primary small" id="btn-apply-override">Apply</button>
                <button class="btn-ghost small" id="btn-remove-override">Remove</button>
                <button class="btn-ghost small" id="btn-reset-all-overrides">Reset All</button>
              </div>
            </div>
            <div id="active-overrides" class="active-overrides"></div>
          </div>
        </section>

        <!-- PRESETS -->
        <section class="panel" id="panel-presets">
          <div class="panel-header collapsible" data-target="presets-body">
            🎬 Scenarios
            <span class="chevron">›</span>
          </div>
          <div id="presets-body" class="panel-body collapsed">
            <div class="preset-grid" id="preset-grid">
              <!-- Generated by presets.js -->
            </div>
          </div>
        </section>

        <!-- FIND ROUTES BUTTON -->
        <div class="find-routes-wrap">
          <button id="btn-find-routes" class="btn-find-routes" disabled>
            <span class="btn-icon">🔍</span>
            <span class="btn-text">Find Routes</span>
          </button>
          <button id="btn-clear" class="btn-clear" title="Clear markers and results">✕</button>
        </div>

      </div><!-- /sidebar-inner -->
    </aside><!-- /sidebar -->

    <!-- MAP -->
    <div id="map-container">
      <div id="map"></div>

      <!-- Map overlay controls (floating, bottom-right) -->
      <div id="overlay-controls">
        <div class="overlay-label">Overlays</div>
        <button class="overlay-btn active" data-overlay="traffic"  title="Traffic heatmap">🌡️</button>
        <button class="overlay-btn" data-overlay="snow"            title="Snow priority">❄️</button>
        <button class="overlay-btn" data-overlay="events"          title="Event closures">🎭</button>
        <button class="overlay-btn" data-overlay="schools"         title="School zones">🏫</button>
        <button class="overlay-btn" data-overlay="scenic"          title="Scenic corridors">🌿</button>
        <button class="overlay-btn" data-overlay="markets"         title="Saturday markets">🛒</button>
        <button class="overlay-btn" data-overlay="hotspots"        title="Tourist hotspots">🏛️</button>
        <button class="overlay-btn" data-overlay="roadworks"       title="Road works">🚧</button>
        <button class="overlay-btn" data-overlay="wind"            title="Wind direction">💨</button>
      </div>

      <!-- Loading spinner (shown during API calls) -->
      <div id="map-loading" class="map-loading hidden">
        <div class="spinner"></div>
        <div id="loading-text">Computing 8 algorithms…</div>
      </div>
    </div>

    <!-- RESULTS DRAWER -->
    <div id="results-drawer" class="results-drawer collapsed">
      <div id="drawer-handle" class="drawer-handle">
        <div class="handle-bar"></div>
        <span id="drawer-summary" class="drawer-summary"></span>
        <button id="drawer-toggle" class="btn-ghost small">▲ Expand</button>
      </div>
      <div id="drawer-body" class="drawer-body">
        <!-- Header -->
        <div class="results-header">
          <div class="results-title">
            <span id="results-route-label">—</span>
          </div>
          <div class="results-meta" id="results-meta"></div>
          <div class="results-sort">
            Sort:
            <button class="sort-btn active" data-sort="distance">Distance</button>
            <button class="sort-btn" data-sort="time">Time</button>
            <button class="sort-btn" data-sort="nodes">Nodes</button>
            <button class="sort-btn" data-sort="compute">Speed</button>
          </div>
        </div>

        <!-- Comparison table -->
        <div class="table-wrap">
          <table id="results-table" class="results-table">
            <thead>
              <tr>
                <th>Algorithm</th>
                <th>Distance</th>
                <th>Est. Time</th>
                <th class="col-nodes">Nodes ↓</th>
                <th class="col-compute">Compute</th>
                <th>Gap</th>
              </tr>
            </thead>
            <tbody id="results-tbody">
              <!-- Populated by results.js -->
            </tbody>
          </table>
        </div>

        <!-- Footer -->
        <div class="results-footer">
          <div id="results-footer-stats" class="footer-stats"></div>
          <div class="results-actions">
            <button class="btn-ghost small" id="btn-explainer">📊 Algorithm Explainer</button>
            <button class="btn-ghost small" id="btn-export-json">📤 Export JSON</button>
          </div>
        </div>
      </div>
    </div>

  </main>

  <!-- ALGORITHM EXPLAINER MODAL -->
  <div id="explainer-modal" class="modal hidden">
    <div class="modal-backdrop" id="modal-backdrop"></div>
    <div class="modal-panel">
      <div class="modal-header">
        <span class="modal-title">Algorithm Explainer</span>
        <button class="modal-close" id="btn-modal-close">✕</button>
      </div>
      <div class="modal-tabs" id="explainer-tabs"></div>
      <div class="modal-body" id="explainer-body"></div>
      <div class="modal-footer">
        <button class="btn-ghost" id="btn-explainer-prev">◄ Previous</button>
        <button class="btn-ghost" id="btn-explainer-next">Next ►</button>
      </div>
    </div>
  </div>

  <!-- App scripts -->
  <script src="/js/api.js"></script>
  <script src="/js/map.js"></script>
  <script src="/js/sidebar.js"></script>
  <script src="/js/overlays.js"></script>
  <script src="/js/results.js"></script>
  <script src="/js/explainer.js"></script>
  <script src="/js/presets.js"></script>
  <script src="/js/app.js"></script>
</body>
</html>
```

---

## Task 6.2 — CSS

**File:** `public/css/style.css`

Implement the following sections in order. Each section is independent — implement
and visually verify before moving to the next.

### A — CSS Reset & Variables
```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg-deep:      #0d1117;
  --bg-panel:     #161b22;
  --bg-surface:   #1c2128;
  --bg-hover:     #22272e;
  --border:       #30363d;
  --text-primary: #e6edf3;
  --text-muted:   #8b949e;
  --accent:       #C9A84C;
  --accent-dim:   rgba(201,168,76,0.15);
  --accent-glow:  rgba(201,168,76,0.3);
  --green:        #3fb950;
  --amber:        #d29922;
  --red:          #f85149;
  --font-display: 'Playfair Display', Georgia, serif;
  --font-ui:      'DM Sans', system-ui, sans-serif;
  --font-mono:    'DM Mono', 'Fira Code', monospace;
  --radius:       8px;
  --radius-sm:    4px;
  --sidebar-w:    340px;
  --topbar-h:     52px;
  --drawer-h:     44px; /* collapsed handle height */
  --transition:   0.18s ease;
}

html, body {
  height: 100%;
  font-family: var(--font-ui);
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-deep);
  overflow: hidden;
}
```

### B — Top Bar
```css
#topbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: var(--topbar-h);
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 16px;
  z-index: 1000;
}

.app-logo { font-size: 20px; }

.app-title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.02em;
}

.topbar-center { flex: 1; display: flex; justify-content: center; }

.weather-badge {
  display: flex; align-items: center; gap: 8px;
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: 20px; padding: 4px 14px;
  color: var(--text-primary); font-family: var(--font-ui);
  font-size: 13px; cursor: pointer; transition: border-color var(--transition);
}
.weather-badge:hover { border-color: var(--accent); }

.mode-label { color: var(--text-muted); font-size: 12px; }

/* Mode toggle — pill style */
.mode-toggle { cursor: pointer; user-select: none; }
.mode-toggle input { display: none; }
.toggle-track {
  display: flex; align-items: center; gap: 6px;
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: 20px; padding: 3px 10px;
  font-size: 12px; color: var(--text-muted);
  transition: background var(--transition);
}
.mode-toggle input:checked ~ .toggle-track { border-color: var(--accent); }
.toggle-thumb {
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--text-muted); transition: all var(--transition);
}
.mode-toggle input:checked ~ .toggle-track .toggle-thumb {
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent-glow);
}
.toggle-label-right { color: var(--text-primary); }

.heuristic-badge {
  background: var(--accent-dim); border: 1px solid var(--accent);
  border-radius: 12px; padding: 2px 10px;
  font-size: 12px; color: var(--accent); cursor: pointer;
}
```

### C — Layout
```css
#app-layout {
  position: fixed;
  top: var(--topbar-h); left: 0; right: 0; bottom: 0;
  display: flex;
}

#map-container {
  flex: 1; position: relative; overflow: hidden;
}

#map {
  width: 100%; height: 100%;
}
```

### D — Sidebar
```css
#sidebar {
  width: var(--sidebar-w);
  background: var(--bg-panel);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow: hidden;
  z-index: 100;
  flex-shrink: 0;
}

#sidebar-inner {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex; flex-direction: column; gap: 8px;
  /* Custom scrollbar */
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.panel {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
}

.panel-header {
  font-size: 11px; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--text-muted); margin-bottom: 10px;
  display: flex; align-items: center; justify-content: space-between;
}

.panel-header.collapsible { cursor: pointer; }
.panel-header.collapsible:hover { color: var(--text-primary); }

.chevron {
  font-size: 16px; color: var(--text-muted);
  transition: transform var(--transition);
}
.panel-header.open .chevron { transform: rotate(90deg); }

.panel-body { overflow: hidden; }
.panel-body.collapsed { display: none; }

/* Advanced-only panels — hidden unless advanced mode active */
.advanced-only { display: none; }
body.advanced-mode .advanced-only { display: block; }
```

### E — Location Inputs
```css
.field-label {
  font-size: 11px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-bottom: 5px; display: flex; align-items: center; gap: 6px;
}

.pin {
  width: 20px; height: 20px; border-radius: 50%;
  font-size: 10px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
}
.pin-start { background: var(--green); color: #000; }
.pin-goal  { background: var(--red);   color: #fff; }

.location-input-wrap {
  display: flex; gap: 6px;
}

.location-input {
  flex: 1; background: var(--bg-deep); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 8px 10px;
  color: var(--text-primary); font-family: var(--font-ui); font-size: 13px;
  outline: none; transition: border-color var(--transition);
}
.location-input:focus { border-color: var(--accent); }
.location-input::placeholder { color: var(--text-muted); }

.coord-display {
  font-family: var(--font-mono); font-size: 11px;
  margin-top: 3px; min-height: 16px;
}

.btn-locate {
  background: var(--bg-deep); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 0 10px;
  cursor: pointer; font-size: 14px; color: var(--text-muted);
  transition: all var(--transition);
}
.btn-locate:hover { border-color: var(--accent); color: var(--accent); }
```

### F — Vehicle Grid
```css
.vehicle-grid {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px;
}

.vehicle-btn {
  background: var(--bg-deep); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 10px 6px;
  font-size: 20px; cursor: pointer; text-align: center;
  transition: all var(--transition);
  line-height: 1;
}
.vehicle-btn:hover { border-color: var(--accent); background: var(--accent-dim); }
.vehicle-btn.active {
  border-color: var(--accent); background: var(--accent-dim);
  box-shadow: 0 0 8px var(--accent-glow);
}
```

### G — Route Profile Tabs
```css
.profile-tabs {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
}

.profile-tab {
  background: var(--bg-deep); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 10px 6px;
  cursor: pointer; text-align: center;
  font-size: 12px; color: var(--text-muted);
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  transition: all var(--transition);
}
.profile-tab .profile-icon { font-size: 18px; }
.profile-tab:hover { border-color: var(--accent); color: var(--text-primary); }
.profile-tab.active {
  border-color: var(--accent); background: var(--accent-dim);
  color: var(--accent); font-weight: 500;
}
```

### H — Time Controls
```css
.time-row {
  display: flex; gap: 8px; margin-bottom: 8px;
}

.input-field {
  flex: 1; background: var(--bg-deep); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 6px 8px;
  color: var(--text-primary); font-family: var(--font-ui); font-size: 13px;
  outline: none; transition: border-color var(--transition);
}
.input-field:focus { border-color: var(--accent); }

/* Override browser date/time input styling */
input[type="date"], input[type="time"] {
  color-scheme: dark;
}

.time-slider-wrap {
  display: flex; align-items: center; gap: 8px;
}

.hour-slider {
  flex: 1; -webkit-appearance: none; height: 4px;
  background: var(--border); border-radius: 2px; outline: none;
}
.hour-slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 16px; height: 16px;
  border-radius: 50%; background: var(--accent);
  cursor: pointer; box-shadow: 0 0 6px var(--accent-glow);
}

.time-label-display {
  text-align: center; font-family: var(--font-mono);
  font-size: 13px; color: var(--accent); margin-top: 6px;
}

.inline-toggle {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--text-muted);
  cursor: pointer; margin-left: auto;
}
.inline-toggle input[type="checkbox"] { accent-color: var(--accent); }
```

### I — Sliders (param sliders)
```css
.slider-row {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 0;
}
.slider-row label {
  font-size: 12px; color: var(--text-muted);
  width: 90px; flex-shrink: 0;
}
.param-slider {
  flex: 1; -webkit-appearance: none; height: 3px;
  background: var(--border); border-radius: 2px; outline: none;
}
.param-slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 14px; height: 14px;
  border-radius: 50%; background: var(--accent); cursor: pointer;
}
.slider-val {
  font-family: var(--font-mono); font-size: 12px;
  color: var(--text-primary); width: 60px; text-align: right;
}
```

### J — Heuristic List
```css
.heuristic-list {
  display: flex; flex-direction: column; gap: 4px;
  max-height: 260px; overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.heuristic-item {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 8px; border-radius: var(--radius-sm);
  cursor: pointer; transition: background var(--transition);
}
.heuristic-item:hover { background: var(--bg-hover); }
.heuristic-item input[type="checkbox"] { accent-color: var(--accent); }
.heuristic-item .h-name { font-size: 12px; flex: 1; }
.heuristic-item .h-badge {
  font-size: 10px; padding: 1px 6px;
  background: var(--accent-dim); border: 1px solid var(--accent);
  border-radius: 10px; color: var(--accent);
  font-family: var(--font-mono);
}

/* Live weight bars */
.weight-breakdown { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border); }
.weight-bar-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 5px;
}
.weight-bar-label { font-size: 11px; color: var(--text-muted); width: 110px; }
.weight-bar-track {
  flex: 1; height: 6px; background: var(--border); border-radius: 3px; overflow: hidden;
}
.weight-bar-fill {
  height: 100%; border-radius: 3px; transition: width 0.3s ease;
}
.weight-bar-fill.low    { background: var(--green); }
.weight-bar-fill.medium { background: var(--amber); }
.weight-bar-fill.high   { background: var(--red); }
.weight-bar-val {
  font-size: 11px; font-family: var(--font-mono);
  color: var(--text-primary); width: 36px; text-align: right;
}
.composite-row {
  font-size: 12px; color: var(--text-muted); padding-top: 6px;
  text-align: right;
}
.composite-row strong { color: var(--accent); font-family: var(--font-mono); }
```

### K — Find Routes Button
```css
.find-routes-wrap {
  display: flex; gap: 8px; margin-top: 4px;
}

.btn-find-routes {
  flex: 1; background: var(--accent); border: none;
  border-radius: var(--radius); padding: 12px;
  color: #000; font-family: var(--font-ui); font-size: 14px;
  font-weight: 600; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: all var(--transition);
}
.btn-find-routes:hover:not(:disabled) {
  background: #e0b95a;
  box-shadow: 0 0 16px var(--accent-glow);
}
.btn-find-routes:disabled {
  opacity: 0.4; cursor: not-allowed;
}
.btn-find-routes.loading {
  background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent);
}

.btn-clear {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 0 14px;
  color: var(--text-muted); cursor: pointer; font-size: 14px;
  transition: all var(--transition);
}
.btn-clear:hover { border-color: var(--red); color: var(--red); }

/* Other button variants */
.btn-primary {
  background: var(--accent); border: none; border-radius: var(--radius-sm);
  padding: 6px 12px; color: #000; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all var(--transition);
}
.btn-secondary {
  background: transparent; border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 5px 10px;
  color: var(--text-muted); font-size: 12px; cursor: pointer;
  transition: all var(--transition);
}
.btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
.btn-ghost {
  background: transparent; border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 4px 10px;
  color: var(--text-muted); font-size: 12px; cursor: pointer;
  transition: all var(--transition);
}
.btn-ghost:hover { border-color: var(--text-muted); color: var(--text-primary); }
.small { font-size: 11px; padding: 3px 8px; }
```

### L — Results Drawer
```css
#results-drawer {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  background: var(--bg-panel);
  border-top: 1px solid var(--border);
  z-index: 200;
  display: flex; flex-direction: column;
  transition: height var(--transition);
  max-height: 50vh;
}

#results-drawer.collapsed {
  height: var(--drawer-h);
  overflow: hidden;
}
#results-drawer.expanded {
  height: 44vh;
}

.drawer-handle {
  height: var(--drawer-h); padding: 0 16px;
  display: flex; align-items: center; gap: 12px;
  cursor: pointer; flex-shrink: 0;
  border-bottom: 1px solid var(--border);
}
.handle-bar {
  width: 40px; height: 4px; background: var(--border);
  border-radius: 2px; flex-shrink: 0;
}
.drawer-summary { flex: 1; font-size: 12px; color: var(--text-muted); }

.drawer-body { flex: 1; overflow: hidden; display: flex; flex-direction: column; }

.results-header {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 16px; flex-shrink: 0;
}
.results-title {
  font-family: var(--font-display); font-size: 14px;
  flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.results-sort { display: flex; gap: 4px; flex-shrink: 0; }
.sort-btn {
  background: none; border: 1px solid transparent;
  border-radius: var(--radius-sm); padding: 2px 8px;
  font-size: 11px; color: var(--text-muted); cursor: pointer;
  transition: all var(--transition);
}
.sort-btn:hover { border-color: var(--border); color: var(--text-primary); }
.sort-btn.active { border-color: var(--accent); color: var(--accent); }

.table-wrap { flex: 1; overflow-y: auto; }

.results-table {
  width: 100%; border-collapse: collapse;
  font-size: 13px;
}
.results-table th {
  position: sticky; top: 0;
  background: var(--bg-panel); padding: 8px 12px;
  font-size: 11px; font-weight: 500; color: var(--text-muted);
  text-align: left; text-transform: uppercase; letter-spacing: 0.05em;
  border-bottom: 1px solid var(--border);
}
.results-table td {
  padding: 10px 12px; border-bottom: 1px solid var(--border);
  font-family: var(--font-mono); font-size: 13px;
}

.result-row { cursor: pointer; transition: background var(--transition); }
.result-row:hover { background: var(--bg-hover); }
.result-row.selected { background: var(--accent-dim); }

/* Algorithm name column */
.algo-name { display: flex; align-items: center; gap: 8px; }
.algo-dot {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}

/* Gap badges */
.gap-badge {
  display: inline-block; padding: 2px 7px; border-radius: 10px;
  font-size: 11px; font-weight: 600;
}
.gap-optimal { background: rgba(63,185,80,0.15); color: var(--green); border: 1px solid var(--green); }
.gap-near    { background: rgba(210,153,34,0.15); color: var(--amber); border: 1px solid var(--amber); }
.gap-far     { background: rgba(248,81,73,0.15); color: var(--red);   border: 1px solid var(--red);   }

/* Nodes expanded mini bar */
.nodes-cell { display: flex; align-items: center; gap: 6px; }
.nodes-bar-track {
  flex: 1; height: 4px; background: var(--border); border-radius: 2px;
  max-width: 60px;
}
.nodes-bar-fill { height: 100%; border-radius: 2px; background: var(--text-muted); }

.results-footer {
  padding: 8px 16px; border-top: 1px solid var(--border);
  display: flex; align-items: center; gap: 16px;
  flex-shrink: 0;
}
.footer-stats { flex: 1; font-size: 12px; color: var(--text-muted); }
.results-actions { display: flex; gap: 8px; }
```

### M — Overlay Controls (Map)
```css
#overlay-controls {
  position: absolute; bottom: 60px; right: 12px;
  background: var(--bg-panel); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 8px;
  display: flex; flex-direction: column; gap: 4px;
  z-index: 500;
}
.overlay-label { font-size: 10px; color: var(--text-muted); text-align: center; margin-bottom: 2px; }
.overlay-btn {
  width: 36px; height: 36px; border-radius: var(--radius-sm);
  background: var(--bg-surface); border: 1px solid var(--border);
  font-size: 16px; cursor: pointer; transition: all var(--transition);
  display: flex; align-items: center; justify-content: center;
}
.overlay-btn:hover { border-color: var(--accent); }
.overlay-btn.active { background: var(--accent-dim); border-color: var(--accent); }

/* Loading spinner */
.map-loading {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  background: var(--bg-panel); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px 30px;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  z-index: 600;
}
.spinner {
  width: 32px; height: 32px; border: 3px solid var(--border);
  border-top-color: var(--accent); border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.hidden { display: none !important; }
```

### N — Modal
```css
.modal {
  position: fixed; inset: 0; z-index: 2000;
  display: flex; align-items: center; justify-content: center;
}
.modal.hidden { display: none; }
.modal-backdrop {
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
}
.modal-panel {
  position: relative; background: var(--bg-panel);
  border: 1px solid var(--border); border-radius: var(--radius);
  width: min(640px, 90vw); max-height: 80vh;
  display: flex; flex-direction: column; overflow: hidden;
}
.modal-header {
  padding: 16px 20px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center;
}
.modal-title {
  font-family: var(--font-display); font-size: 16px; flex: 1;
}
.modal-close {
  background: none; border: none; color: var(--text-muted);
  font-size: 16px; cursor: pointer; padding: 4px;
}
.modal-tabs {
  display: flex; gap: 4px; padding: 8px 16px;
  border-bottom: 1px solid var(--border); flex-wrap: wrap;
}
.explainer-tab {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 4px 10px;
  font-size: 12px; cursor: pointer; transition: all var(--transition);
}
.explainer-tab.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
.modal-body {
  flex: 1; overflow-y: auto; padding: 20px;
  font-size: 14px; line-height: 1.7; color: var(--text-primary);
}
.modal-footer {
  padding: 12px 20px; border-top: 1px solid var(--border);
  display: flex; justify-content: space-between;
}

/* Miscellaneous */
.muted { color: var(--text-muted); }
.small { font-size: 11px; }

/* Weather/heuristic grids */
.weather-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px;
  margin-bottom: 8px;
}
.weather-btn {
  background: var(--bg-deep); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 6px 4px;
  font-size: 14px; cursor: pointer; text-align: center;
  color: var(--text-muted); font-size: 12px;
  transition: all var(--transition);
}
.weather-btn:hover { border-color: var(--accent); }
.weather-btn.active { border-color: var(--accent); background: var(--accent-dim); }
.weather-btn small { display: block; font-size: 10px; margin-top: 2px; }

.heuristic-actions { display: flex; gap: 6px; margin-bottom: 8px; }

/* Preset grid */
.preset-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
}
.preset-btn {
  background: var(--bg-deep); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 8px 10px;
  text-align: left; cursor: pointer; font-size: 12px; color: var(--text-muted);
  display: flex; flex-direction: column; gap: 2px;
  transition: all var(--transition);
}
.preset-btn:hover { border-color: var(--accent); color: var(--text-primary); }
.preset-btn .preset-icon { font-size: 18px; }
.preset-btn .preset-name { font-size: 11px; font-weight: 500; color: var(--text-primary); }
.preset-btn .preset-desc { font-size: 10px; color: var(--text-muted); }

/* Leaflet popup override */
.leaflet-popup-content-wrapper {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  color: var(--text-primary) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
}
.leaflet-popup-tip { background: var(--bg-panel) !important; }
.leaflet-popup-content { margin: 12px 16px !important; font-family: var(--font-ui) !important; }
```

---

## Task 6.3 — JavaScript Modules

Implement these JS files in order. Each is described with its responsibilities,
key functions, and data it reads/writes.

### `public/js/api.js`

Wraps all fetch calls to the FastAPI backend.

```javascript
const API_BASE = '';  // same origin

const Api = {
  async findPath(params) {
    const resp = await fetch(`${API_BASE}/api/find-path`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(params),
    });
    if (!resp.ok) throw new Error(`API error ${resp.status}`);
    return resp.json();
  },

  async getWeather() {
    const resp = await fetch(`${API_BASE}/api/weather`);
    return resp.json();
  },

  async setOverride(edgeId, intensity) {
    return fetch(`${API_BASE}/api/manual-override`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({edge_id: edgeId, intensity}),
    });
  },

  async clearOverrides() {
    return fetch(`${API_BASE}/api/manual-override`, {method: 'DELETE'});
  },

  async getGraphStats() {
    const resp = await fetch(`${API_BASE}/api/graph/stats`);
    return resp.json();
  },
};
```

### `public/js/map.js`

Responsibilities: Leaflet map init, start/goal marker placement, route polyline
drawing, road click handler, overlay layer management.

Key functions to implement:
- `MapManager.init()` — creates Leaflet map with dark basemap
- `MapManager.setStartMarker(lat, lon)` — animated green pin
- `MapManager.setGoalMarker(lat, lon)` — animated red pin
- `MapManager.drawRoutes(results)` — draws all 8 coloured polylines simultaneously
  with staggered animation (100ms between each)
- `MapManager.selectRoute(algorithmName)` — bolds selected route; dims others
- `MapManager.clearRoutes()` — removes all route layers
- `MapManager.onRoadClick(callback)` — installs click handler on road segments
  (use `e.latlng` + nearest edge lookup to find the clicked edge)

**Map tile — use dark CartoDB:**
```javascript
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '© OpenStreetMap © CARTO',
  subdomains: 'abcd',
  maxZoom: 19,
}).addTo(map);
```

**Custom marker SVG:**
```javascript
function makePin(color, label) {
  return L.divIcon({
    className: 'custom-pin',
    html: `<div style="
      width:28px;height:36px;
      background:${color};
      border-radius:50% 50% 50% 0;
      transform:rotate(-45deg);
      border:2px solid white;
      display:flex;align-items:center;justify-content:center;
    ">
      <span style="transform:rotate(45deg);color:white;font-weight:700;font-size:12px;">${label}</span>
    </div>`,
    iconSize: [28, 36],
    iconAnchor: [14, 36],
  });
}
```

### `public/js/sidebar.js`

Responsibilities: All sidebar UI logic — vehicle selection, time controls,
heuristic checkboxes, weight bars, collapsible panels, mode toggle.

Key constants:
```javascript
const HEURISTICS_METADATA = [
  {id: 'weather',           name: 'Weather',              icon: '⛅', always: true},
  {id: 'time_of_day',       name: 'Time of Day',          icon: '🕐', always: true},
  {id: 'vehicle_type',      name: 'Vehicle Type',         icon: '🚗', always: true},
  {id: 'intersection',      name: 'Intersection Density', icon: '🔴'},
  {id: 'surface',           name: 'Surface/Pavement',     icon: '🧱'},
  {id: 'elevation',         name: 'Elevation/Slope',      icon: '⛰️'},
  {id: 'safety',            name: 'Safety/Lighting',      icon: '💡'},
  {id: 'emission_zones',    name: 'Emission Zones',       icon: '🌫️'},
  {id: 'headway',           name: 'Transit Headway',      icon: '🚇'},
  {id: 'tram_tracks',       name: 'Tram Track Hazard',    icon: '🚃'},
  {id: 'wind',              name: 'Wind Resistance',      icon: '💨'},
  {id: 'parking',           name: 'Parking Search Time',  icon: '🅿️'},
  {id: 'scenic',            name: 'Scenic/Greenery',      icon: '🌿'},
  {id: 'school_zones',      name: 'School Zones',         icon: '🏫'},
  {id: 'holiday',           name: 'Holidays/Hotspots',    icon: '🏛️'},
  {id: 'events',            name: 'Event Roadblocks',     icon: '🎭'},
  {id: 'fiaker',            name: 'Fiaker (Carriages)',   icon: '🐴'},
  {id: 'snow_priority',     name: 'MA48 Snow Priority',   icon: '❄️'},
  {id: 'commuter_bridges',  name: 'Commuter Bridges',     icon: '🌉'},
  {id: 'markets',           name: 'Saturday Markets',     icon: '🛒'},
  {id: 'heuriger',          name: 'Heuriger Season',      icon: '🍷'},
  {id: 'season',            name: 'Season Modifier',      icon: '🍂'},
  {id: 'lane_capacity',     name: 'Lane Capacity',        icon: '🛣️'},
  {id: 'road_works',        name: 'Road Works',           icon: '🚧'},
  {id: 'pedestrian_density',name: 'Pedestrian Density',   icon: '👥'},
  {id: 'delivery',          name: 'Delivery Windows',     icon: '📦'},
];
```

### `public/js/results.js`

Responsibilities: Populate results drawer, handle row clicks, sorting, animate
route colours, update drawer summary bar.

```javascript
const ALGO_COLORS = {
  dijkstra:           '#C9A84C',
  astar:              '#3fb950',
  weighted_astar:     '#58a6ff',
  bidirectional_astar:'#79c0ff',
  greedy:             '#f78166',
  ucs:                '#a5d6ff',
  bfs:                '#d2a8ff',
  dfs:                '#ffa657',
};

const ALGO_DISPLAY_NAMES = {
  dijkstra:           'Dijkstra',
  astar:              'A*',
  weighted_astar:     'Weighted A*',
  bidirectional_astar:'Bidirectional A*',
  greedy:             'Greedy Best-First',
  ucs:                'UCS',
  bfs:                'BFS',
  dfs:                'DFS',
};
```

### `public/js/app.js`

The main orchestrator. Connects all modules together. Handles:
- The click-to-set-start/goal flow
- Collecting all sidebar state into a params object
- Calling `Api.findPath(params)` when FIND ROUTES is clicked
- Passing results to `Results.render()` and `MapManager.drawRoutes()`
- Auto-refreshing weather every 10 minutes
- Keyboard shortcut registration

### `public/js/presets.js`

```javascript
const PRESETS = [
  {
    id: 'marathon',
    icon: '🏃', name: 'Marathon Day',
    desc: 'Vienna City Marathon — Ringstraße closed',
    config: {date:'2026-04-19', hour:8, weather:'clear', vehicle:'car'},
  },
  {
    id: 'blizzard',
    icon: '❄️', name: 'Blizzard',
    desc: 'Heavy snow, morning rush, all districts',
    config: {weather:'heavy_snow', hour:8, day_of_week:1, vehicle:'car'},
  },
  {
    id: 'christmas',
    icon: '🎄', name: 'Christmas Market',
    desc: 'December Saturday afternoon',
    config: {date:'2026-12-12', hour:14, weather:'light_snow', vehicle:'walking'},
  },
  {
    id: 'bike_rain',
    icon: '🚴', name: 'Bike in Rain',
    desc: 'Morning commute, rain, tram track hazard',
    config: {weather:'rain', hour:8, day_of_week:1, vehicle:'bicycle'},
  },
  {
    id: 'heuriger',
    icon: '🍷', name: 'Heuriger Night',
    desc: 'October Friday evening, Grinzing destination',
    config: {month:10, day_of_week:4, hour:20, weather:'clear', vehicle:'car'},
  },
  {
    id: 'late_walk',
    icon: '🌙', name: 'Late Night Walk',
    desc: '2 AM walking — safety lighting matters',
    config: {hour:2, vehicle:'walking', weather:'clear'},
  },
  {
    id: 'donauinselfest',
    icon: '🎶', name: 'Donauinselfest',
    desc: 'Massive festival, Danube Island area',
    config: {date:'2026-06-27', hour:14, weather:'clear'},
  },
];
```

### `public/js/explainer.js`

Generates contextual algorithm explanations using the last run's data.

```javascript
function buildExplanation(algoName, result, allResults) {
  const dijkstraResult = allResults['dijkstra'];
  const nodesVsDijkstra = dijkstraResult
    ? Math.round((1 - result.nodes_expanded / dijkstraResult.nodes_expanded) * 100)
    : 0;

  const explanations = {
    astar: `
      A* is the gold standard for pathfinding. It combines the actual cost to
      reach a node (g) with a heuristic estimate of remaining distance (h).
      By balancing both, it focuses exploration toward the goal rather than
      spreading in all directions like Dijkstra.

      In this run: A* expanded ${result.nodes_expanded} nodes vs Dijkstra's
      ${dijkstraResult?.nodes_expanded} — that's ${nodesVsDijkstra}% less work.
      It found ${result.is_optimal ? 'the optimal path' : 'a near-optimal path'}
      in just ${result.compute_time_ms?.toFixed(1)}ms.
    `,
    // ... one entry per algorithm
  };
  return explanations[algoName] || 'No explanation available.';
}
```

---

> **Checkpoint 6 done.** The full UI is working. Open the app, select two points
> on Vienna's map, click Find Routes. All 8 routes should animate onto the map,
> the results drawer should slide up, and clicking rows should highlight routes.

---

---

# SPRINT 7 — Polish & Map Overlays

**Goal:** Complete overlay system, manual road override popups, responsive mobile
layout, scenario presets animations, keyboard shortcuts, and performance tuning.

---

## Task 7.1 — Map Overlays

**File:** `public/js/overlays.js`

Each overlay is a separate Leaflet layer group. Overlays are toggled via the
overlay control buttons. Some overlays are context-sensitive (school zones
pulse only when the active time is in a school window).

```javascript
const OVERLAY_DEFS = {
  traffic: {
    label: 'Traffic heatmap',
    build: (graph, params) => buildTrafficHeatmap(graph, params),
    // Colours each edge from green→red based on its composite heuristic cost
  },
  snow: {
    label: 'Snow priority network',
    build: (graph, params) => buildSnowOverlay(graph),
    // Priority A edges = cyan glow polylines; B = dark blue
  },
  events: {
    label: 'Active event closures',
    build: (graph, params) => buildEventOverlay(params.date, params.hour),
    // Red hatched polygons around event zones
  },
  schools: {
    label: 'School drop-off zones',
    build: (graph, params) => buildSchoolOverlay(params.hour, params.day_of_week),
    // Yellow pulsing circles around school nodes
  },
  scenic: {
    label: 'Scenic corridors',
    build: (graph, params) => buildScenicOverlay(graph),
    // Blue-green shimmer polylines along near_green_space edges
  },
  markets: {
    label: 'Saturday market zones',
    build: (graph, params) => buildMarketOverlay(params.day_of_week, params.hour),
    // Purple radius circles around market coords
  },
  hotspots: {
    label: 'Tourist hotspots',
    build: (graph, params) => buildHotspotOverlay(),
    // Semi-transparent gold circles at hotspot coords
  },
  roadworks: {
    label: 'Road works (Baustellen)',
    build: (graph, params) => buildRoadWorksOverlay(params.date),
    // Orange diagonal-stripe zone polygons
  },
  wind: {
    label: 'Wind direction',
    build: (graph, params) => buildWindArrows(params.wind_speed, params.wind_deg),
    // Animated white arrow markers at regular intervals across the map
  },
};
```

---

## Task 7.2 — Road Click Popup

When the user clicks a road segment on the map, a popup appears showing:
- Road name, type, surface, speed limit, lanes
- Active heuristic multipliers for this edge (from the last API response)
- Traffic override slider

This requires a nearest-edge lookup: given a click `lat/lon`, find the closest
edge in `vienna_graph.json`. Implement `nearestEdge(lat, lon, graph)` in
`map.js` — iterate all edges and use the perpendicular distance from the point
to each segment line.

```javascript
function perpDistToSegment(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx*dx + dy*dy)));
  return Math.hypot(px - (ax + t*dx), py - (ay + t*dy));
}
```

---

## Task 7.3 — Responsive Mobile Layout

Add to `style.css`:

```css
@media (max-width: 768px) {
  #sidebar {
    position: fixed; bottom: 0; left: 0; right: 0;
    width: 100%; height: auto; max-height: 60vh;
    top: auto; border-right: none; border-top: 1px solid var(--border);
    z-index: 300;
    transform: translateY(calc(100% - 56px));
    transition: transform var(--transition);
  }
  #sidebar.open { transform: translateY(0); }

  #map-container { width: 100%; }

  #results-drawer { bottom: 60px; }
}
```

---

## Task 7.4 — Keyboard Shortcuts

In `app.js`:

```javascript
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;  // don't intercept text fields
  const map = {
    's': () => document.getElementById('input-start').focus(),
    'g': () => document.getElementById('input-goal').focus(),
    'Enter': () => document.getElementById('btn-find-routes').click(),
    'Escape': closeAllModals,
    'a': () => document.getElementById('advanced-toggle').click(),
    'r': () => document.getElementById('btn-reset-all-overrides').click(),
    '?': showKeyboardHelp,
  };
  // Number keys 1–8: select algorithm row
  if (e.key >= '1' && e.key <= '8') {
    selectAlgorithmRow(parseInt(e.key) - 1);
  }
  map[e.key]?.();
});
```

---

> **Checkpoint 7 done.** Full application is working. Test all 7 scenario presets.
> Test mobile view in browser devtools. Verify all overlays toggle correctly.
> Run all 8 algorithms with `vehicle=bicycle, weather=heavy_rain, hour=8` and
> confirm that A\* and Dijkstra return identical distances.

---

---

# Heuristics Reference

> This section is the implementation reference for Sprint 5. Each heuristic is
> described with its exact lookup tables and function signatures. Claude Code
> should implement them one file at a time, adding each to `combined.py`
> immediately after implementation.

---

## H-01: Intersection Density

```python
# src/heuristics/intersection_density.py

ZONE_MULTIPLIERS = {
    "1": 1.3, "2": 1.1, "3": 1.1, "7": 1.2, "8": 1.2,  # dense inner districts
    "highway": 0.8,  # artificial zone for motorways
}

def get_intersection_penalty(node_id, graph):
    degree = len(graph["adjacency"].get(node_id, []))
    if degree <= 2:
        return 1.0
    base = 1.0 + (degree - 2) * 0.05  # +5% per extra connecting road
    node = graph["nodes"][node_id]
    if node.get("has_traffic_signal"):
        base += 0.10
    district = node.get("district", "unknown")
    return base * ZONE_MULTIPLIERS.get(district, 1.0)
```

---

## H-02: Surface / Pavement

```python
# src/heuristics/surface.py

SURFACE_PENALTIES = {
    # surface: {vehicle: multiplier}
    "cobblestone": {"car":1.05, "motorcycle":1.1, "bicycle":1.6, "walking":1.1, "bus":1.15, "escooter":1.7},
    "sett":        {"car":1.03, "motorcycle":1.05,"bicycle":1.4, "walking":1.05,"bus":1.1,  "escooter":1.5},
    "unpaved":     {"car":1.15, "motorcycle":1.2, "bicycle":1.8, "walking":1.2, "bus":1.3,  "escooter":2.0},
    "gravel":      {"car":1.15, "motorcycle":1.2, "bicycle":1.8, "walking":1.2, "bus":1.3,  "escooter":2.0},
    "metal":       {"car":1.1,  "motorcycle":1.3, "bicycle":1.9, "walking":1.2, "bus":1.0,  "escooter":2.0},
}

def get_surface_multiplier(edge, vehicle_type):
    surface = edge.get("surface", "asphalt")
    if surface in ("asphalt", "paved", "concrete"):
        return 1.0
    return SURFACE_PENALTIES.get(surface, {}).get(vehicle_type, 1.0)
```

---

## H-03 through H-22

> Claude Code: implement each following the same pattern. The full specification
> for each heuristic (lookup tables, function logic, OSM tag dependencies) is
> in the v2 plan document. Each file should be ~30–80 lines. Wire each into
> `combined.py`'s `make_heuristic()` factory after completing it.

---

---

# Data Reference

## Vienna Hotspot Coordinates

| Place | Lat | Lon | Radius |
|-------|-----|-----|--------|
| Stephansdom | 48.2085 | 16.3721 | 500m |
| Schönbrunn | 48.1847 | 16.3122 | 500m |
| Hofburg | 48.2066 | 16.3644 | 500m |
| Belvedere | 48.1916 | 16.3800 | 500m |
| Karlskirche | 48.1980 | 16.3719 | 400m |
| Prater | 48.2165 | 16.3955 | 600m |
| Naschmarkt | 48.1988 | 16.3635 | 300m |
| Rathaus | 48.2100 | 16.3570 | 400m |
| Museum Quartier | 48.2037 | 16.3607 | 400m |

## Key Bridge Edges

| Bridge | Approx midpoint | Penalty (rush hour) |
|--------|----------------|---------------------|
| Reichsbrücke | 48.2267, 16.4108 | 1.8× |
| Nordbrücke | 48.2444, 16.3858 | 1.6× |
| Floridsdorfer Brücke | 48.2533, 16.3956 | 1.5× |
| Stadionbrücke | 48.2068, 16.3975 | 1.4× |
| Südosttangente A23 | 48.1744, 16.3970 | 2.0× |

## Viennese Market Coordinates

| Market | Lat | Lon | Day | Hours |
|--------|-----|-----|-----|-------|
| Brunnenmarkt | 48.2197 | 16.3453 | Sat | 08–13 |
| Karmelitermarkt | 48.2145 | 16.3845 | Sat | 06–14 |
| Naschmarkt | 48.1988 | 16.3635 | Daily | 06–19 |
| Rochusmarkt | 48.2030 | 16.3925 | Sat | 06–13 |
| Yppenplatz | 48.2013 | 16.3378 | Sat | 08–13 |

## Heuriger Zone Coordinates

| Zone | Lat | Lon | Radius | Active |
|------|-----|-----|--------|--------|
| Grinzing | 48.2645 | 16.3483 | 400m | Sep–Oct, Fri–Sat 16–23 |
| Neustift am Walde | 48.2450 | 16.3250 | 300m | Sep–Oct, Fri–Sat 16–23 |
| Stammersdorf | 48.2883 | 16.4217 | 300m | Sep–Oct, Fri–Sat 16–23 |
| Mauer | 48.1433 | 16.3183 | 300m | Sep–Oct, Fri–Sat 16–23 |

## Austrian Public Holidays 2026

| Date | Name |
|------|------|
| 2026-01-01 | Neujahr |
| 2026-01-06 | Heilige Drei Könige |
| 2026-04-06 | Ostermontag |
| 2026-05-01 | Staatsfeiertag |
| 2026-05-14 | Christi Himmelfahrt |
| 2026-05-25 | Pfingstmontag |
| 2026-06-04 | Fronleichnam |
| 2026-08-15 | Mariä Himmelfahrt |
| 2026-10-26 | Nationalfeiertag |
| 2026-11-01 | Allerheiligen |
| 2026-12-08 | Mariä Empfängnis |
| 2026-12-25 | Christtag |
| 2026-12-26 | Stefanitag |

---

---

# Common Issues & Debugging

## Overpass Returns Empty

- The API may be rate-limited. Wait 60 seconds and retry.
- Try a different mirror (see `osm_fetcher.py`).
- Check your internet connection.
- Verify the query with Overpass Turbo: `https://overpass-turbo.eu`

## Graph Has Too Few Nodes (<500)

- The curation threshold may be too strict. Reduce the `haversine` radius checks
  in `select_nodes` from 600m to 1000m for hotspot proximity.
- Check that `DISTRICT_BOUNDS` covers all 23 districts. Nodes outside all
  bounding boxes are classified as `"unknown"` district and may be pruned.

## Algorithm Takes >5 Seconds

- The graph is probably too large. Check `graph["meta"]["node_count"]`.
  Target is 800–1 200 nodes.
- Add a timeout in `runner.py` using `concurrent.futures.wait(timeout=3)`.
- For DFS specifically, add a depth limit: `if len(path) > 500: continue`.

## Routes Don't Appear on Map

- Check the browser console for JavaScript errors.
- Verify the API response: `fetch('/api/find-path', {method:'POST', ...}).then(r=>r.json()).then(console.log)`
- Check that `path_coords` in the response is a non-empty list of `[lat, lon]` pairs.
- Verify node IDs: `nearest_node()` may return `None` if the lat/lon is outside
  Vienna. Add bounds checking.

## Weather API Returns 401

- Your OpenWeatherMap API key is invalid or not yet active (takes up to 2 hours after signup).
- The `/api/weather` endpoint has a fallback — it returns default values if the key is missing.

## Dark Map Tiles Not Loading

- The CartoDB dark tile URL has `{r}` for retina. Replace with `@2x` on high-DPI
  screens or use the non-retina URL: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png`

---

# Sprint Summary

| Sprint | Days | Deliverable |
|--------|------|-------------|
| 0 (Setup) | 0 | Project structure, venv, dependencies |
| 1 (Data) | 1–2 | `vienna_graph.json` with ~1 000 nodes |
| 2 (Algorithms) | 3–4 | All 8 algorithms running in parallel |
| 3 (API) | 5–6 | FastAPI server, `/api/find-path` working |
| 4 (Core Heuristics) | 7–8 | Weather, time, vehicle affecting routes |
| 5 (Vienna Heuristics) | 9–11 | All 22 local factors active |
| 6 (Frontend) | 12–15 | Full beautiful UI, all 8 routes on map |
| 7 (Polish) | 16–18 | Overlays, presets, mobile, shortcuts |
