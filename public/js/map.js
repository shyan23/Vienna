/* map.js — Leaflet init, markers, route polylines, road-click handler */
const MapManager = (() => {
  let map = null;
  let startMarker = null;
  let goalMarker  = null;
  let routeLayers = {};      // algoKey -> L.polyline
  let bboxLayer   = null;    // graph coverage rectangle
  let selectedKey = null;
  let onStartChange = null;
  let onGoalChange  = null;
  let onRoadClick   = null;
  let getPendingChange = null;  // () => 'start' | 'goal' | null

  // distinct, high-contrast colors for the 8 algorithms
  const ALGO_COLORS = {
    bfs:              '#ff6b6b',
    dfs:              '#ffb86c',
    ucs:              '#ffcc66',
    dijkstra:         '#48c78e',
    greedy:           '#4ecdc4',
    astar:            '#6ea8fe',
    weighted_astar:   '#b794f4',
    bidirectional_astar: '#e056a0',
  };

  function makePin(letter, color) {
    const html = `
      <div style="
        width:30px;height:40px;position:relative;
        filter: drop-shadow(0 3px 6px rgba(0,0,0,0.5));
      ">
        <svg viewBox="0 0 30 40" width="30" height="40">
          <path d="M15 0 C6 0 0 6 0 14 C0 22 15 40 15 40 C15 40 30 22 30 14 C30 6 24 0 15 0 Z"
            fill="${color}" stroke="#0b0f14" stroke-width="1.5"/>
          <circle cx="15" cy="14" r="8" fill="#0b0f14"/>
        </svg>
        <div style="
          position:absolute; top:6px; left:0; width:30px; height:18px;
          text-align:center; color:#fff; font-weight:800; font-size:12px;
          font-family:'DM Mono', monospace;">${letter}</div>
      </div>`;
    return L.divIcon({
      html, className: 'custom-pin',
      iconSize: [30, 40], iconAnchor: [15, 40],
    });
  }

  function init(containerId, { center = [48.2082, 16.3738], zoom = 13 } = {}) {
    map = L.map(containerId, {
      center, zoom, zoomControl: true, attributionControl: true,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '© OpenStreetMap · © CARTO',
    }).addTo(map);

    map.on('click', (ev) => {
      const { lat, lng } = ev.latlng;
      const pending = getPendingChange ? getPendingChange() : null;

      if (pending === 'start') {
        setStartMarker(lat, lng);
        onStartChange && onStartChange(lat, lng);
      } else if (pending === 'goal') {
        setGoalMarker(lat, lng);
        onGoalChange && onGoalChange(lat, lng);
      } else if (!startMarker) {
        setStartMarker(lat, lng);
        onStartChange && onStartChange(lat, lng);
      } else if (!goalMarker) {
        setGoalMarker(lat, lng);
        onGoalChange && onGoalChange(lat, lng);
      }
      // Both set and no pending change → ignore clicks (use ✎ buttons to change)
    });

    return map;
  }

  function setStartMarker(lat, lon) {
    if (startMarker) map.removeLayer(startMarker);
    startMarker = L.marker([lat, lon], { icon: makePin('A', '#48c78e') }).addTo(map);
  }
  function setGoalMarker(lat, lon) {
    if (goalMarker) map.removeLayer(goalMarker);
    goalMarker = L.marker([lat, lon], { icon: makePin('B', '#ff6b6b') }).addTo(map);
  }
  function clearMarkers() {
    if (startMarker) { map.removeLayer(startMarker); startMarker = null; }
    if (goalMarker)  { map.removeLayer(goalMarker);  goalMarker  = null; }
  }

  function clearRoutes() {
    for (const k of Object.keys(routeLayers)) map.removeLayer(routeLayers[k]);
    routeLayers = {};
    selectedKey = null;
  }

  function drawRoutes(results) {
    clearRoutes();
    showRouteLegend(results);
    const sorted = Object.entries(results).filter(([, r]) => r && r.path_coords && r.path_coords.length > 1);
    // Draw each with a small stagger for a nice reveal effect
    sorted.forEach(([key, r], i) => {
      const color = ALGO_COLORS[key] || '#6ea8fe';
      setTimeout(() => {
        const line = L.polyline(r.path_coords, {
          color,
          weight: 4,
          opacity: 0.75,
          lineJoin: 'round',
          className: `route-line route-${key}`,
        }).addTo(map);
        line.on('click', () => selectRoute(key));
        routeLayers[key] = line;
      }, i * 100);
    });
    // Fit bounds to all coords across results
    const all = sorted.flatMap(([, r]) => r.path_coords);
    if (all.length) {
      setTimeout(() => map.fitBounds(L.latLngBounds(all).pad(0.1)), sorted.length * 100 + 50);
    }
  }

  function selectRoute(key) {
    selectedKey = key;
    for (const [k, layer] of Object.entries(routeLayers)) {
      if (k === key) {
        layer.setStyle({ weight: 7, opacity: 1.0 });
        layer.bringToFront();
      } else {
        layer.setStyle({ weight: 3, opacity: 0.35 });
      }
    }
  }

  function drawGraphBbox(bbox) {
    // bbox = [min_lat, min_lon, max_lat, max_lon]
    if (!bbox || bbox.length < 4) return;
    if (bboxLayer) map.removeLayer(bboxLayer);

    const [minLat, minLon, maxLat, maxLon] = bbox;
    const bounds = [[minLat, minLon], [maxLat, maxLon]];

    bboxLayer = L.rectangle(bounds, {
      color:     '#C9A84C',   // gold accent
      weight:    2,
      opacity:   0.8,
      fillColor: '#C9A84C',
      fillOpacity: 0.04,
      dashArray: '6 4',
      interactive: false,
    }).addTo(map);

    bboxLayer.bindTooltip(
      '📍 Graph coverage — click inside this area to set Origin / Destination',
      { permanent: false, direction: 'center', className: 'bbox-tooltip' }
    );
  }

  // ── Route legend on the map ──────────────────────────────────────────
  let legendControl = null;

  function showRouteLegend(results) {
    if (legendControl) { map.removeControl(legendControl); legendControl = null; }
    const valid = Object.entries(results).filter(([, r]) => r && r.path_coords && r.path_coords.length > 1);
    if (valid.length === 0) return;

    const ALGO_LABELS = {
      bfs: 'BFS', dfs: 'DFS', ucs: 'Uniform-Cost', dijkstra: 'Dijkstra',
      greedy: 'Greedy', astar: 'A*', weighted_astar: 'Weighted A*',
      bidirectional_astar: 'Bidirectional A*',
    };

    legendControl = L.control({ position: 'topright' });
    legendControl.onAdd = function () {
      const div = L.DomUtil.create('div', 'route-legend');
      const title = document.createElement('div');
      title.className = 'legend-title';
      title.textContent = 'Routes';
      div.appendChild(title);

      for (const [key] of valid) {
        const color = ALGO_COLORS[key] || '#6ea8fe';
        const label = ALGO_LABELS[key] || key;
        const item = document.createElement('div');
        item.className = 'legend-item';
        item.dataset.key = key;

        const swatch = document.createElement('span');
        swatch.className = 'legend-swatch';
        swatch.style.background = color;
        const lbl = document.createElement('span');
        lbl.className = 'legend-label';
        lbl.textContent = label;

        item.appendChild(swatch);
        item.appendChild(lbl);
        item.addEventListener('click', () => selectRoute(key));
        div.appendChild(item);
      }
      return div;
    };
    legendControl.addTo(map);
  }

  // ── Blocked / congested road markers ──────────────────────────────────
  let blockedLayers = [];

  function drawBlockedRoads(overrides, graphNodes) {
    // overrides = [{ edge_id: "from_to", intensity: 100 }, ...]
    // graphNodes = { nodeId: { lat, lon }, ... }
    clearBlockedRoads();
    if (!overrides || !graphNodes) return;

    for (const ov of overrides) {
      const [fromId, toId] = ov.edge_id.split('_');
      const fromNode = graphNodes[fromId];
      const toNode   = graphNodes[toId];
      if (!fromNode || !toNode) continue;

      const blocked = ov.intensity >= 95;
      const color   = blocked ? '#ff2222' : '#ff8800';  // red = blocked, orange = congested
      const label   = blocked ? '🚫 Blocked' : '⚠️ Heavy traffic';

      const line = L.polyline(
        [[fromNode.lat, fromNode.lon], [toNode.lat, toNode.lon]],
        {
          color,
          weight: 6,
          opacity: 0.9,
          dashArray: blocked ? '8 6' : '4 4',
          className: 'blocked-road',
        }
      ).addTo(map);
      line.bindTooltip(label, { permanent: false, direction: 'top' });
      blockedLayers.push(line);
    }
  }

  function clearBlockedRoads() {
    for (const l of blockedLayers) map.removeLayer(l);
    blockedLayers = [];
  }

  function onStart(fn)         { onStartChange   = fn; }
  function onGoal(fn)          { onGoalChange    = fn; }
  function onPendingChange(fn) { getPendingChange = fn; }
  function getMap()            { return map; }

  return {
    init, setStartMarker, setGoalMarker, clearMarkers,
    drawRoutes, selectRoute, clearRoutes, drawGraphBbox,
    drawBlockedRoads, clearBlockedRoads,
    onStart, onGoal, onPendingChange, getMap, ALGO_COLORS,
  };
})();
