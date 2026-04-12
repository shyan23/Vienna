"""
Vienna OSM graph builder.

Takes raw Overpass JSON and produces a curated adjacency-list graph:
~1 000 nodes, ~10 000 edges. Each edge stores distance_m plus a set of
enriched tags used by the heuristics in Sprint 4/5.
"""
from __future__ import annotations

import math

from src.graph.osm_fetcher import VIENNA_BBOX

# --------------------------------------------------------------------------- #
# Lookup tables
# --------------------------------------------------------------------------- #

ROAD_TYPE_DEFAULTS = {
    "motorway": 130,
    "trunk": 100,
    "primary": 50,
    "secondary": 50,
    "tertiary": 30,
    "residential": 30,
    "living_street": 10,
    "pedestrian": 5,
    "footway": 5,
    "cycleway": 20,
    "steps": 2,
    "subway": 80,
    "tram": 40,
    "light_rail": 80,
}

# Approximate bounding boxes for Vienna's 23 districts.
# Format: district -> (min_lat, min_lon, max_lat, max_lon)
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

TOURIST_HOTSPOTS = [
    (48.2085, 16.3721, "Stephansdom"),
    (48.1847, 16.3122, "Schönbrunn"),
    (48.2066, 16.3644, "Hofburg"),
    (48.1916, 16.3800, "Belvedere"),
    (48.1980, 16.3719, "Karlskirche"),
    (48.2165, 16.3955, "Prater"),
    (48.1988, 16.3635, "Naschmarkt"),
    (48.2100, 16.3570, "Rathaus"),
    (48.2037, 16.3607, "Museum Quartier"),
]

MAJOR_ROAD_TYPES = {"motorway", "trunk", "primary", "secondary"}

BRIDGE_KEYWORDS = {
    "Reichsbrücke",
    "Nordbrücke",
    "Floridsdorfer",
    "Stadionbrücke",
    "Schwedenbrücke",
    "Donaustadtbrücke",
    "Praterbrücke",
    "brücke",
    "Brücke",
}


# --------------------------------------------------------------------------- #
# Geometry helpers
# --------------------------------------------------------------------------- #

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns great-circle distance in metres between two lat/lon points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_district(lat: float, lon: float) -> str:
    for district, (min_lat, min_lon, max_lat, max_lon) in DISTRICT_BOUNDS.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return district
    return "unknown"


# --------------------------------------------------------------------------- #
# Parsing & enrichment
# --------------------------------------------------------------------------- #

def parse_osm(raw_data: dict) -> tuple[dict, list]:
    """
    Convert Overpass JSON into node/way dicts.

    Returns:
        nodes: {node_id (str) -> {"lat", "lon", "tags"}}
        ways:  [{"id", "nodes": [id,...], "tags"}]
    """
    nodes: dict[str, dict] = {}
    ways: list[dict] = []
    for elem in raw_data.get("elements", []):
        if elem["type"] == "node":
            nodes[str(elem["id"])] = {
                "lat": elem["lat"],
                "lon": elem["lon"],
                "tags": elem.get("tags", {}),
            }
        elif elem["type"] == "way":
            ways.append(
                {
                    "id": elem["id"],
                    "nodes": [str(n) for n in elem.get("nodes", [])],
                    "tags": elem.get("tags", {}),
                }
            )
    return nodes, ways


def enrich_way_tags(tags: dict) -> dict:
    """Convert raw OSM tags to structured edge metadata."""
    highway = tags.get("highway", tags.get("railway", "residential"))

    maxspeed_raw = tags.get("maxspeed", "")
    try:
        maxspeed = (
            int(str(maxspeed_raw).split()[0])
            if maxspeed_raw
            else ROAD_TYPE_DEFAULTS.get(highway, 30)
        )
    except (ValueError, IndexError):
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
        "lit": tags.get(
            "lit",
            "yes" if highway in ("primary", "secondary", "tertiary") else "unknown",
        ),
        "lanes": lanes,
        "tram_track": (
            tags.get("railway") == "tram" or tags.get("embedded_rails") == "yes"
        ),
        "cycle_infra": tags.get("cycleway", tags.get("cycleway:right", "none")),
        "bus_route": tags.get("bus") == "yes",
        "bridge": tags.get("bridge") == "yes",
        "tunnel": tags.get("tunnel") == "yes",
        "motor_vehicle": tags.get("motor_vehicle", "yes"),
    }


# --------------------------------------------------------------------------- #
# Node curation
# --------------------------------------------------------------------------- #

def select_nodes(nodes: dict, ways: list, target: int = 5000) -> set[str]:
    """
    Return a set of node IDs representing the curated subgraph, capped at target.

    Priorities (higher = selected first):
      5 — 1st district intersections (degree ≥ 2)
      4 — Major arteries (motorway/trunk/primary/secondary) and bridges
      3 — Tourist hotspot neighbourhoods (within ~600 m)
      2 — U-Bahn / S-Bahn station nodes
      1 — Sampled residential nodes per district
    """
    # Build node-degree counter
    node_way_count: dict[str, int] = {}
    for way in ways:
        for nid in way["nodes"]:
            node_way_count[nid] = node_way_count.get(nid, 0) + 1

    # Assign priority scores to every node
    scores: dict[str, int] = {}

    def add(nid: str, score: int) -> None:
        if nid in nodes:
            scores[nid] = max(scores.get(nid, 0), score)

    # Priority 5 — 1st district intersections
    for nid, node in nodes.items():
        if get_district(node["lat"], node["lon"]) == "1" and node_way_count.get(nid, 0) >= 2:
            add(nid, 5)

    # Priority 4 — major roads and bridges
    for way in ways:
        tags = way["tags"]
        road_type = tags.get("highway", tags.get("railway", ""))
        name = tags.get("name", "")
        is_bridge = tags.get("bridge") == "yes" or any(k in name for k in BRIDGE_KEYWORDS)
        is_major = road_type in MAJOR_ROAD_TYPES or tags.get("railway") in (
            "subway",
            "light_rail",
            "tram",
        )
        if is_major or is_bridge:
            for nid in way["nodes"]:
                add(nid, 4)

    # Priority 3 — tourist hotspot neighbourhoods
    for nid, node in nodes.items():
        lat, lon = node["lat"], node["lon"]
        for (hlat, hlon, _name) in TOURIST_HOTSPOTS:
            if haversine(lat, lon, hlat, hlon) < 600:
                add(nid, 3)
                break

    # Priority 2 — transit station nodes
    for nid, node in nodes.items():
        ntags = node.get("tags", {})
        if ntags.get("railway") in ("station", "stop", "halt") or ntags.get("public_transport") == "station":
            add(nid, 2)

    # Priority 1 — sampled residential nodes per district
    per_district: dict[str, list[str]] = {}
    for nid, node in nodes.items():
        d = get_district(node["lat"], node["lon"])
        per_district.setdefault(d, []).append(nid)
    for _d, nids in per_district.items():
        step = max(1, len(nids) // 50)
        for nid in nids[::step]:
            add(nid, 1)

    # Sort by score descending, take top `target`
    ranked = sorted(scores.keys(), key=lambda n: scores[n], reverse=True)
    selected = set(ranked[:target])

    print(f"[Builder] Selected {len(selected):,} nodes after curation (target={target})")
    return selected


# --------------------------------------------------------------------------- #
# Graph assembly
# --------------------------------------------------------------------------- #

def build_graph(nodes: dict, ways: list, selected_node_ids: set[str]) -> dict:
    """Build the final adjacency-list graph from the curated node set."""
    graph_nodes: dict[str, dict] = {}
    for nid in selected_node_ids:
        if nid not in nodes:
            continue
        node = nodes[nid]
        ntags = node.get("tags", {})
        graph_nodes[nid] = {
            "lat": node["lat"],
            "lon": node["lon"],
            "district": get_district(node["lat"], node["lon"]),
            "name": ntags.get("name", ""),
            "has_traffic_signal": ntags.get("highway") == "traffic_signals",
            "elevation_m": None,  # optional, filled by precompute_elevation.py
        }

    edges: list[dict] = []
    adjacency: dict[str, list] = {nid: [] for nid in graph_nodes}

    for way in ways:
        enriched = enrich_way_tags(way["tags"])
        way_nodes = [n for n in way["nodes"] if n in graph_nodes]
        if len(way_nodes) < 2:
            continue

        for i in range(len(way_nodes) - 1):
            n1, n2 = way_nodes[i], way_nodes[i + 1]
            if n1 == n2:
                continue
            lat1, lon1 = graph_nodes[n1]["lat"], graph_nodes[n1]["lon"]
            lat2, lon2 = graph_nodes[n2]["lat"], graph_nodes[n2]["lon"]
            dist = haversine(lat1, lon1, lat2, lon2)

            snow_priority = (
                "A"
                if enriched["road_type"] in ("primary", "secondary", "trunk", "motorway")
                or enriched["tram_track"]
                else "B"
            )

            edge = {
                **enriched,
                "from": n1,
                "to": n2,
                "distance_m": round(dist, 2),
                "near_school": False,  # filled in Sprint 5 if school coords available
                "near_green_space": False,
                "snow_priority": snow_priority,
            }

            # Always add both directions — the curated subgraph is too sparse
            # for one-way streets to make sense; forcing bidirectionality
            # guarantees routability across the simplified network.
            edge_idx = len(edges)
            edges.append(edge)
            adjacency[n1].append({"node": n2, "edge_idx": edge_idx})

            rev_edge = {**edge, "from": n2, "to": n1}
            rev_idx = len(edges)
            edges.append(rev_edge)
            adjacency[n2].append({"node": n1, "edge_idx": rev_idx})

    # ------------------------------------------------------------------ #
    # Keep only the largest connected component (BFS flood-fill).        #
    # With bidirectional edges this guarantees full routability.          #
    # ------------------------------------------------------------------ #

    visited: set[str] = set()
    components: list[set[str]] = []
    for start in graph_nodes:
        if start in visited:
            continue
        component: set[str] = set()
        queue = [start]
        while queue:
            node = queue.pop()
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for e in adjacency.get(node, []):
                if e["node"] not in visited:
                    queue.append(e["node"])
        components.append(component)

    largest = max(components, key=len) if components else set()
    print(f"[Builder] Components: {len(components)}, largest: {len(largest)} nodes")

    graph_nodes = {n: v for n, v in graph_nodes.items() if n in largest}
    adjacency = {
        n: [e for e in adj if e["node"] in largest]
        for n, adj in adjacency.items()
        if n in largest
    }
    # Re-index edges — keep only edges whose both endpoints survived
    surviving = {e["edge_idx"] for adj in adjacency.values() for e in adj}
    edges = [e for i, e in enumerate(edges) if i in surviving]
    old_to_new = {old: new for new, old in enumerate(sorted(surviving))}
    for adj in adjacency.values():
        for e in adj:
            e["edge_idx"] = old_to_new[e["edge_idx"]]

    # Compute actual bounding box from surviving nodes
    lats = [n["lat"] for n in graph_nodes.values()]
    lons = [n["lon"] for n in graph_nodes.values()]
    actual_bbox = [min(lats), min(lons), max(lats), max(lons)] if lats else list(VIENNA_BBOX)

    return {
        "nodes": graph_nodes,
        "edges": edges,
        "adjacency": adjacency,
        "meta": {
            "node_count": len(graph_nodes),
            "edge_count": len(edges),
            "bbox": actual_bbox,
        },
    }
