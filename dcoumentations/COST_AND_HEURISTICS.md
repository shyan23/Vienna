# Vienna Routing: Cost and Heuristics Documentation

This document explains how distances are measured, how edge costs ($g(n)$) are calculated, and how heuristics ($h(n)$) are combined to guide search algorithms like A*.

---

## 1. Distance Calculation

All distance measurements in the Vienna project use the **Haversine Formula**. This calculates the great-circle distance (the shortest distance over the Earth's surface) between two points defined by their latitude and longitude.

- **Formula**:
  $$a = \sin^2(\frac{\Delta\phi}{2}) + \cos(\phi_1)\cos(\phi_2)\sin^2(\frac{\Delta\lambda}{2})$$
  $$c = 2 \cdot \operatorname{atan2}(\sqrt{a}, \sqrt{1-a})$$
  $$d = R \cdot c$$
  Where $R = 6,371,000$ meters (Earth's radius), $\phi$ is latitude, and $\lambda$ is longitude.
- **Unit**: All distances are stored and processed in **meters (m)**.

### Source Code Implementation
In `src/graph/builder.py`:
```python
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns great-circle distance in metres between two lat/lon points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
```

---

## 2. Edge Cost ($g(n)$)

The edge cost, also known as the path cost from the start to the current node ($g(n)$), represents the actual weight assigned to an edge in the graph.

### Effective Cost Calculation
When a path is being searched, the base distance is modified by several factors.

1.  **Manual Traffic Overrides**:
    - **Blocked**: If intensity $\ge 95$, the edge is considered impassable ($\infty$ cost).
    - **Sub-blocked**: If intensity $< 95$, the cost is multiplied by:
      $$\text{Multiplier} = 0.5 + (\frac{\text{intensity}}{100.0}) \cdot 2.5$$
      *(This scales cost from $0.5\times$ for empty roads to $2.85\times$ for heavy traffic)*.

2.  **Road Quality Multiplier**:
    To make routing "time-equivalent," the cost is adjusted based on road type and surface.

### Source Code Implementation
In `src/graph/loader.py` -> `get_effective_edge_cost()`:
```python
    if overrides_map:
        edge_key = f'{edge["from"]}_{edge["to"]}'
        if edge_key in overrides_map:
            intensity = overrides_map[edge_key]
            if intensity >= 95:
                return float("inf")
            cost *= 0.5 + (intensity / 100.0) * 2.5

    if params is not None and params.get("use_road_quality", True):
        from src.heuristics.road_quality import get_road_quality_multiplier
        cost *= get_road_quality_multiplier(edge, params.get("vehicle_type"))
```

---

## 3. Heuristic Cost ($h(n)$)

The heuristic cost ($h(n)$) is an estimate of the remaining cost from the current node to the goal. In A*, $f(n) = g(n) + h(n)$.

### Composite Multiplier
The project uses a sophisticated **multiplier-based heuristic** system. The final $h(n)$ is:
$$h(n) = \text{Haversine}(n, \text{goal}) \cdot \text{Multiplier}_{\text{Total}}$$

### Source Code Implementation
In `src/heuristics/combined.py` -> `heuristic()` closure:
```python
        # ---- goal-only multipliers (constant per route but need goal) ---- #
        if _enabled(enabled, "parking"):
            mult *= get_parking_multiplier(goal_district, vehicle)
        # ...

        # ---- node-dependent ---- #
        if _enabled(enabled, "intersection_density"):
            mult *= get_intersection_penalty(node_id, graph)
        # ...

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
                # ...
                if e_mult < best_edge_mult:
                    best_edge_mult = e_mult
            if best_edge_mult != float("inf"):
                mult *= best_edge_mult
```

---

## 4. Admissibility and Capping

### Admissibility
A heuristic is **admissible** if it never overestimates the true cost to reach the goal. The **Haversine distance** is the base admissible heuristic because the straight-line distance between two points on the map is always shorter than or equal to the shortest path through the road segments of the graph.

However, many heuristics (like weather penalties, traffic overrides, and surface roughness) multiply the distance by factors $> 1.0$, which can make the heuristic **inadmissible**.

### The MAX_HEURISTIC_CAP
To prevent the search from becoming purely greedy and losing track of optimal alternatives, the final heuristic is capped:

$$h(n)_{\text{final}} = \min(h, h_{\text{base}} \cdot \text{MAX\_HEURISTIC\_CAP})$$

- **Default CAP**: 50.0 (configurable via the `MAX_HEURISTIC_CAP` environment variable).
- **Maintenance of $\epsilon$-admissibility**: By capping the multiplier, the algorithm remains **bounded-suboptimal**. This means that even with extreme penalties, the resulting path is guaranteed to be within a known factor of the optimal path.

### How Capping Helps
1.  **Search Focus**: It keeps the search "grounded" by preventing $h(n)$ from ballooning to astronomical values that would completely dwarf the actual cost $g(n)$.
2.  **Greedy Prevention**: Without a cap, A* would behave like a Greedy Best-First Search on high-penalty routes, blindly following the lowest $h$ without exploring better $g+h$ alternatives.
3.  **Stability**: It ensures that search performance remains consistent even when multiple heavy multipliers (e.g., Heavy Snow + Black Ice + Night Network + Traffic) are stacked together.

### Source Code Implementation
In `src/heuristics/combined.py`:
```python
MAX_HEURISTIC_CAP = float(os.getenv("MAX_HEURISTIC_CAP", "50.0"))
# ...
        h = h_base * mult
        # Cap total h against arbitrary blow-up, keep ε-admissibility
        return min(h, h_base * MAX_HEURISTIC_CAP)
```

---

## 5. Distance and Time Results

Once a path is found, the final metrics are calculated as follows:

- **Total Distance (`distance_m`)**: The sum of the raw `distance_m` values of all edges in the path.
- **Estimated Time (`estimated_time_s`)**:
  $$\text{Time} = \frac{\sum \text{Raw Distances}}{\text{Vehicle Constant Speed}}$$

### Source Code Implementation
In `src/algorithms/base.py`:
```python
def sum_path_distance(graph: dict, path: list[str]) -> float:
    """Sum the edge distances along a node path. Returns 0 if path is empty."""
    # ... loops through path and sums graph["edges"][edge_idx]["distance_m"] ...

VEHICLE_SPEEDS = {
    "car":        8.33,   # ~30 km/h urban
    "motorcycle": 9.72,   # ~35 km/h
}
```
