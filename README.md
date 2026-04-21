# Vienna Traffic Router

A web app that runs **8 classic AI search algorithms** (BFS, DFS, UCS, Dijkstra,
Greedy Best-First, A\*, Weighted A\*, Bidirectional A\*) on Vienna's road network
and shows all 8 routes simultaneously on an interactive dark-mode Leaflet map.

**22+ tunable heuristics** model weather, time of day, vehicle type, and
Vienna-specific local effects (tram tracks, Fiaker carriages, Heuriger zones,
commuter bridges, Saturday markets, snow priority, and more).

## Quick start

```bash
# 1. Set up a virtual env and install deps
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Copy env template and (optionally) add an OpenWeatherMap key
cp .env.example .env

# 3. Fetch Vienna OSM data and build the curated graph (~1–3 min, one time)
python scripts/fetch_osm_data.py

# 4. Start the server
uvicorn src.main:app --reload --port 8000

# 5. Open http://localhost:8000
```

## Architecture

- **Backend** — Python 3.11 + FastAPI. Graph is loaded once at startup from
  `data/vienna_graph.json`. Each request kicks off 8 algorithms in a
  `ThreadPoolExecutor` and returns a unified comparison response.
- **Algorithms** — all implement the same `find_path(graph, start, goal, h_fn, params)`
  signature and return a `PathResult` dataclass. See [ALGORITHMS.md](dcoumentations/ALGORITHMS.md) for details.
- **Heuristics** — `src/heuristics/combined.py` exposes `make_heuristic(params)`
  which composes all active sub-heuristics into a single callable `h(node, goal, graph)`.
  Detailed logic in [COST_AND_HEURISTICS.md](dcoumentations/COST_AND_HEURISTICS.md).
- **Frontend** — vanilla JS + Leaflet. No build step. Dark "Imperial Vienna"
  theme with gold accent, comparison table drawer, overlays, and scenario presets.

## Repo layout

See `CLAUDE_CODE_GUIDE.md` for the full build guide and design spec.
