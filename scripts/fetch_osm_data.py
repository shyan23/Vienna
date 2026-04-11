#!/usr/bin/env python3
"""
One-time script to download Vienna OSM data and build the curated graph.

Run:
    python scripts/fetch_osm_data.py

Output:
    data/vienna_raw.json     (~30–80 MB, cached 30 days)
    data/vienna_graph.json   (~2–5 MB, the graph your app uses)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph.builder import build_graph, parse_osm, select_nodes  # noqa: E402
from src.graph.osm_fetcher import fetch_vienna_osm  # noqa: E402

RAW_PATH = Path("data/vienna_raw.json")
GRAPH_PATH = Path("data/vienna_graph.json")


def main() -> None:
    print("=" * 60)
    print("Vienna Traffic Router — Graph Builder")
    print("=" * 60)

    # Step 1 — fetch (or load cached) raw OSM data
    raw = fetch_vienna_osm(RAW_PATH)

    # Step 2 — parse
    print("[Builder] Parsing OSM elements...")
    nodes, ways = parse_osm(raw)
    print(f"[Builder] Parsed {len(nodes):,} nodes, {len(ways):,} ways")

    # Step 3 — curate
    selected = select_nodes(nodes, ways)

    # Step 4 — build
    print("[Builder] Building graph...")
    graph = build_graph(nodes, ways, selected)

    # Step 5 — save
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
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
