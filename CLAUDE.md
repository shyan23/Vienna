# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Vienna Traffic Router** — a FastAPI + vanilla-JS web app that runs **8 classic AI search algorithms** (BFS, DFS, UCS, Dijkstra, Greedy Best-First, A\*, Weighted A\*, Bidirectional A\*) in parallel on a curated subgraph of Vienna's OpenStreetMap road network (~1 000 nodes, ~10 000 edges), shows all 8 resulting routes on a Leaflet map, and lets the user tune 30+ heuristic parameters (weather, time of day, vehicle type, and Vienna-specific local effects) to watch the routes change in real time.

The authoritative build guide is **`CLAUDE_CODE_GUIDE.md`** at the repo root — it's the spec the implementation follows. Read it when you need the "why" behind a design choice.

## Commands

```bash
# Setup (one time)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: add OPENWEATHERMAP_API_KEY

# Build the graph (one time, ~1–3 min; cached 30 days)
python scripts/fetch_osm_data.py

# Run the dev server (hot reload)
uvicorn src.main:app --reload --port 8000
# → frontend at http://localhost:8000, API at http://localhost:8000/api/...

# Quick smoke test without the full graph — every module compiles:
python -m compileall src scripts
```

There is **no test suite or lint config yet**. Add tests under a new `tests/` directory following `pytest` conventions when testing new work.

## Architecture — the big picture

Reading the code top-down means following the data flow of a single request:

### 1. Request dispatch (`src/main.py` → `src/routes/api.py`)

`FindPathRequest` (Pydantic) carries **every** tunable parameter the frontend can set in one payload: start/goal coords, weather, hour/day/month/date, vehicle_type, route_profile, environmental sliders (temperature/humidity/visibility/wind), plus `enabled_heuristics` (a whitelist) and `manual_overrides`. Manual road overrides are held in a module-level `_overrides` dict — there is no DB.

### 2. Heuristic assembly (`src/heuristics/combined.py`)

`make_heuristic(params)` is a **closure factory**. This is the design choice to internalize:

- **Static tier** — multipliers that depend only on `params` (weather, time-of-day, vehicle, visibility, humidity, wind, headway, night network) are resolved **once** at closure-build time into a single float `static_mult`.
- **Dynamic tier** — multipliers that depend on the current node or its outgoing edges (intersection density, surface, elevation, safety, emission, tram tracks, snow, bridges, lane capacity, school, scenic, manual adjustment) are evaluated **per call** inside the returned closure.
- **Goal-dependent** multipliers (parking, holiday, events, fiaker, season, pedestrian density, delivery) are constant per route but still resolved inside the closure because they key off `goal.district`.

A* calls `h(node, goal, graph, params)` thousands of times per route — keeping the static tier out of the hot path is load-bearing for interactive latency.

The edge-dependent sub-heuristics pick the **cheapest outgoing edge** as a proxy for the frontier node (iterating adjacency inside h()). This keeps the heuristic consistent (never overestimates from the same node twice) but still reflects the local road quality.

`MAX_HEURISTIC_CAP` (env var, default 50) caps the composite multiplier so weighted A\* stays **ε-admissible** — bounded suboptimality rather than pathological inadmissibility when many multipliers stack.

The 30 heuristic modules in `src/heuristics/` each expose a single `get_*_multiplier(...)` returning a float. When adding a new one, **also register it in `combined.py`** (import, `ALL_HEURISTIC_IDS` set, and a new `if _enabled(enabled, "my_key"):` branch in the right tier).

### 3. Parallel algorithm execution (`src/algorithms/runner.py`)

`run_all(start_lat, start_lon, goal_lat, goal_lon, params, heuristic_fn)`:

1. Lazy-loads the graph singleton via `src.graph.loader.load_graph()`
2. Snaps the given lat/lon pair to the nearest graph node via `nearest_node()` (linear scan; ~1 000 nodes)
3. Dispatches all 8 algorithms through a `ThreadPoolExecutor(max_workers=8)`
4. Uses **Dijkstra as ground truth** to compute `is_optimal` and `optimality_gap_pct` for every other result
5. Returns a dict of `PathResult`-as-dicts plus timing metadata

Every algorithm implements the same signature:
```python
def find_path(graph, start_id, goal_id, heuristic_fn, params) -> PathResult
```
`PathResult` (in `src/algorithms/base.py`) is the only shape the frontend ever sees from this layer.

### 4. Graph data (`src/graph/`)

- **`osm_fetcher.py`** — Overpass API client with mirror fallback and 30-day JSON cache. Vienna bounding box is a module constant.
- **`builder.py`** — the meat of the data pipeline:
  - `parse_osm` → `select_nodes` (7-tier priority curation to ~1 000 nodes) → `enrich_way_tags` → `build_graph` (adjacency list)
  - `get_district(lat, lon)` uses bounding-box lookup for Vienna's 23 districts — several heuristics key off district strings, so "unknown" propagates to mean "don't apply the penalty"
  - Edge records carry derived booleans (`near_school`, `near_green_space`, `snow_priority`, `tram_track`, `bridge`, `tunnel`, `motor_vehicle`) that the heuristics use without re-parsing tags
- **`loader.py`** — lazy singleton (module-level `_GRAPH`). Resolves from `VIENNA_GRAPH_PATH` env var, default `data/vienna_graph.json`. Call `reset_graph_cache()` in tests.

Edge indexing uses `adjacency[node_id] = [{"node": nb_id, "edge_idx": int}, ...]` — the `edge_idx` points into the flat `edges` list. This shape is load-bearing for the runner and the algorithms; don't flatten it.

### 5. Frontend (`public/`, built in Phase 5+)

Vanilla JS + Leaflet, no bundler. Module split: `api.js` (fetch wrappers), `map.js` (Leaflet map + nearest-edge lookup), `sidebar.js` (input panels, heuristic list generator from `HEURISTICS_METADATA`), `overlays.js` (9 Leaflet layer groups), `results.js` (comparison table + drawer), `explainer.js` (algorithm modal), `presets.js` (scenario buttons), `app.js` (wiring + keyboard shortcuts). Dark "Imperial Vienna" theme — gold `#C9A84C` accent on deep-blue/charcoal panels.

## Conventions worth knowing

- **g(n) and h(n) share the metre unit.** Edge weights are `distance_m` (Haversine). Heuristics return `haversine × multiplier`. Never return "seconds" from a heuristic — the runner converts to time at `DEFAULT_SPEED_MS = 8.33` m/s for display only.
- **Bidirectional A\*** relies on the fact that `build_graph` emits a reverse edge for every non-strictly-oneway way, so forward-adjacency lookups on the goal side already give you predecessors. Don't "fix" this unless you're also rebuilding the reverse-adjacency index.
- **Heuristic enabling** — an empty `enabled_heuristics` list means "all active" (the baseline from the UI's default). A populated list is a strict whitelist. `_enabled(enabled, key)` in `combined.py` encodes this.
- **Manual overrides** — edge keys are `{from}_{to}` strings, intensity 0..100 maps linearly to multiplier 0.5..3.0 (`manual_adjustment.py`).

## Where NOT to look for things

- No tests yet — don't waste time grepping `tests/`.
- No DB/ORM — `_overrides` dict in `src/routes/api.py` is the entire mutable state surface.
- No Docker/CI config in this repo.
- `data/` is gitignored — if `vienna_graph.json` is missing, run `scripts/fetch_osm_data.py`.

## Implementation progress (pre-existing phases)

Phases 1–4 are committed (data pipeline, 8 algorithms, FastAPI backend, 30-heuristic engine). Phases 5–6 (frontend + polish) land in follow-up commits — the `CLAUDE_CODE_GUIDE.md` file is the spec for those.
