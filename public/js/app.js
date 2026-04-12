/* app.js — top-level orchestration: wires sidebar, map, results, explainer */
(function () {
  const VIENNA_CENTER = [48.2082, 16.3738];

  function fmtCoord(lat, lon) {
    return `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  }

  function updateFindButton() {
    const req = Sidebar.buildRequest();
    const btn = document.getElementById('btn-find-routes');
    btn.disabled = !req;
  }

  function showLoading(on, text) {
    const el = document.getElementById('map-loading');
    if (text) document.getElementById('loading-text').textContent = text;
    el.classList.toggle('hidden', !on);
  }

  async function refreshWeather() {
    try {
      const w = await Api.getWeather();
      if (!w) return;
      document.getElementById('weather-icon').textContent = iconFor(w.weather);
      const temp = (w.temp != null) ? w.temp : (w.temperature != null ? w.temperature : 15);
      document.getElementById('weather-temp').textContent = `${Math.round(temp)}°C`;
      document.getElementById('weather-desc').textContent = w.description || w.weather;
      // patch sidebar state with live values
      if (Sidebar && Sidebar.state) {
        Sidebar.state.weather = w.weather || Sidebar.state.weather;
        Sidebar.state.temperature = temp;
        if (w.humidity != null)   Sidebar.state.humidity = w.humidity;
        if (w.wind_speed != null) Sidebar.state.wind_speed = w.wind_speed;
        if (w.wind_deg != null)   Sidebar.state.wind_deg = w.wind_deg;
        if (w.visibility != null) Sidebar.state.visibility_m = w.visibility;
      }
    } catch (e) {
      document.getElementById('weather-desc').textContent = 'offline';
    }
  }

  function iconFor(key) {
    return ({
      clear: '☀', cloudy: '⛅', fog: '🌫', light_rain: '🌦', rain: '🌧',
      thunderstorm: '⛈', light_snow: '🌨', heavy_snow: '❄', black_ice: '🧊',
    })[key] || '🌤';
  }

  async function onFindRoutes() {
    const req = Sidebar.buildRequest();
    if (!req) return;
    // Attach weather-event overrides
    if (weatherOverrides.length > 0) {
      req.manual_overrides = weatherOverrides;
    }
    showLoading(true, 'Computing 8 algorithms…');
    Results.setSummary('Running…');
    try {
      const t0 = performance.now();
      const resp = await Api.findPath(req);
      const dt = (performance.now() - t0).toFixed(0);
      window.__lastResults = resp.results || {};

      // Move markers to snapped graph-node positions so routes visually connect
      if (resp.start_snapped) {
        const [lat, lon] = resp.start_snapped;
        MapManager.setStartMarker(lat, lon);
        Sidebar.setStart(lat, lon);
        document.getElementById('input-start').value = fmtCoord(lat, lon);
        document.getElementById('start-coords').textContent = fmtCoord(lat, lon);
      }
      if (resp.goal_snapped) {
        const [lat, lon] = resp.goal_snapped;
        MapManager.setGoalMarker(lat, lon);
        Sidebar.setGoal(lat, lon);
        document.getElementById('input-goal').value = fmtCoord(lat, lon);
        document.getElementById('goal-coords').textContent = fmtCoord(lat, lon);
      }

      MapManager.drawRoutes(resp.results || {});
      Results.render(resp.results || {});
      const label = document.getElementById('results-route-label');
      if (label) {
        label.textContent =
          `${fmtCoord(req.start_lat, req.start_lon)} → ${fmtCoord(req.goal_lat, req.goal_lon)}`;
      }
      const valid = Object.values(resp.results || {}).filter(r => r && !r.error).length;
      Results.setSummary(`${valid}/8 routes in ${dt} ms — click a row to highlight`);
      Results.expand();
    } catch (err) {
      Results.setSummary(`Error: ${err.message}`);
      console.error(err);
    } finally {
      showLoading(false);
    }
  }

  // Pending-change state: 'start' | 'goal' | null
  let pendingChange = null;

  function showChangeButtons() {
    const hasStart = !!Sidebar.state.start;
    const hasGoal  = !!Sidebar.state.goal;
    document.getElementById('btn-change-start').style.display = hasStart ? '' : 'none';
    document.getElementById('btn-change-goal').style.display  = hasGoal  ? '' : 'none';
  }

  function onClear() {
    pendingChange = null;
    MapManager.clearMarkers();
    MapManager.clearRoutes();
    Sidebar.setStart(null, null); Sidebar.state.start = null;
    Sidebar.setGoal(null, null);  Sidebar.state.goal  = null;
    document.getElementById('input-start').value = '';
    document.getElementById('input-goal').value = '';
    document.getElementById('start-coords').textContent = '';
    document.getElementById('goal-coords').textContent = '';
    showChangeButtons();
    Results.render({});
    Results.setSummary('Click the map to set Origin (A) and Destination (B)');
    updateFindButton();
  }

  function bindKeyboard() {
    document.addEventListener('keydown', (ev) => {
      if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA') return;
      if (ev.key === 'Enter') onFindRoutes();
      else if (ev.key === 'Escape') onClear();
    });
  }

  function bindLocateMe() {
    document.getElementById('btn-locate').addEventListener('click', () => {
      if (!navigator.geolocation) return;
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords;
          MapManager.setStartMarker(latitude, longitude);
          Sidebar.setStart(latitude, longitude);
          document.getElementById('input-start').value = fmtCoord(latitude, longitude);
          document.getElementById('start-coords').textContent = fmtCoord(latitude, longitude);
          MapManager.getMap().setView([latitude, longitude], 14);
          updateFindButton();
          refreshWeather(latitude, longitude);
        },
        (err) => console.warn('Geolocation denied:', err),
      );
    });
  }

  // ── Traffic Boost (Issue 5) ──────────────────────────────────────────────
  let boostRoute = null;  // { key, path_node_ids }

  function boostLabel(v) {
    if (v >= 90) return `${v}% — Blocked`;
    if (v >= 70) return `${v}% — Heavy`;
    if (v >= 40) return `${v}% — Moderate`;
    return `${v}% — Light`;
  }

  function showBoostPanel(key, result) {
    boostRoute = result && result.path_node_ids && result.path_node_ids.length > 1
      ? { key, path_node_ids: result.path_node_ids }
      : null;
    const panel = document.getElementById('traffic-boost-panel');
    if (!boostRoute) { panel.classList.add('hidden'); return; }
    panel.classList.remove('hidden');
    document.getElementById('boost-route-name').textContent =
      Results.ALGO_DISPLAY[key] || key;
    const slider = document.getElementById('boost-slider');
    document.getElementById('boost-val-display').textContent = boostLabel(Number(slider.value));
  }

  function bindBoostPanel() {
    const slider = document.getElementById('boost-slider');
    slider.addEventListener('input', () => {
      document.getElementById('boost-val-display').textContent = boostLabel(Number(slider.value));
    });

    document.getElementById('btn-boost-recalculate').addEventListener('click', async () => {
      if (!boostRoute) return;
      const intensity = Number(document.getElementById('boost-slider').value);
      // Apply override to every edge in the selected route
      const ids = boostRoute.path_node_ids;
      await Api.clearOverrides();
      for (let i = 0; i < ids.length - 1; i++) {
        await Api.setOverride(`${ids[i]}_${ids[i+1]}`, intensity);
      }
      // Also apply reverse direction edges
      for (let i = ids.length - 1; i > 0; i--) {
        await Api.setOverride(`${ids[i]}_${ids[i-1]}`, intensity);
      }
      document.getElementById('traffic-boost-panel').classList.add('hidden');
      boostRoute = null;
      await onFindRoutes();
    });

    document.getElementById('btn-boost-reset').addEventListener('click', async () => {
      await Api.clearOverrides();
      document.getElementById('traffic-boost-panel').classList.add('hidden');
      boostRoute = null;
    });
  }

  // ── Weather Events (Issue 6) ─────────────────────────────────────────────
  // Rolled once when weather changes; applied as manual_overrides in request
  let weatherOverrides = [];

  function rollWeatherEvent(weather) {
    weatherOverrides = [];
    const results = window.__lastResults || {};
    const allPaths = Object.values(results)
      .filter(r => r && r.path_node_ids && r.path_node_ids.length > 1)
      .map(r => r.path_node_ids);
    if (allPaths.length === 0) return;

    function randomEdge() {
      const path = allPaths[Math.floor(Math.random() * allPaths.length)];
      const i = Math.floor(Math.random() * (path.length - 1));
      return `${path[i]}_${path[i+1]}`;
    }

    if (weather === 'heavy_snow') {
      // Blizzard: block 1 random road
      weatherOverrides = [{ edge_id: randomEdge(), intensity: 100 }];
    } else if (weather === 'rain') {
      // Rainy: 2 random roads with severe traffic
      weatherOverrides = [
        { edge_id: randomEdge(), intensity: 85 },
        { edge_id: randomEdge(), intensity: 85 },
      ];
    } else if (weather === 'thunderstorm') {
      // Storm: 1 random road blocked
      weatherOverrides = [{ edge_id: randomEdge(), intensity: 100 }];
    }

    if (weatherOverrides.length > 0) {
      const labels = { heavy_snow: 'Blizzard', rain: 'Heavy Rain', thunderstorm: 'Storm' };
      Results.setSummary(
        `⚠️ ${labels[weather] || weather}: ${weatherOverrides.length} road(s) affected. Re-calculate to see impact.`
      );
    }
  }

  function bindWeatherEvents() {
    // Hook into weather selector clicks
    const weatherGrid = document.getElementById('weather-selector');
    if (!weatherGrid) return;
    weatherGrid.addEventListener('click', (ev) => {
      const btn = ev.target.closest('[data-weather]');
      if (!btn) return;
      const weather = btn.dataset.weather;
      Sidebar.state.weather = weather;
      rollWeatherEvent(weather);
    });
  }

  function init() {
    Sidebar.init();
    const map = MapManager.init('map', { center: VIENNA_CENTER, zoom: 13 });
    Overlays.init(map);
    Results.init();
    Explainer.init();
    Presets.init();

    MapManager.onStart((lat, lon) => {
      pendingChange = null;
      Sidebar.setStart(lat, lon);
      document.getElementById('input-start').value = fmtCoord(lat, lon);
      document.getElementById('start-coords').textContent = fmtCoord(lat, lon);
      showChangeButtons();
      updateFindButton();
    });
    MapManager.onGoal((lat, lon) => {
      pendingChange = null;
      Sidebar.setGoal(lat, lon);
      document.getElementById('input-goal').value = fmtCoord(lat, lon);
      document.getElementById('goal-coords').textContent = fmtCoord(lat, lon);
      showChangeButtons();
      updateFindButton();
    });
    MapManager.onPendingChange(() => pendingChange);

    document.getElementById('btn-change-start').addEventListener('click', () => {
      pendingChange = 'start';
      Results.setSummary('Click the map to set a new Origin (A)');
    });
    document.getElementById('btn-change-goal').addEventListener('click', () => {
      pendingChange = 'goal';
      Results.setSummary('Click the map to set a new Destination (B)');
    });

    Results.onRowClickHandler((key, result) => {
      MapManager.selectRoute(key);
      showBoostPanel(key, result);
    });

    document.getElementById('btn-find-routes').addEventListener('click', onFindRoutes);
    document.getElementById('btn-clear').addEventListener('click', onClear);
    document.getElementById('weather-badge').addEventListener('click', () => refreshWeather());
    document.getElementById('auto-weather-btn').addEventListener('click', () => refreshWeather());
    document.getElementById('btn-export-json').addEventListener('click', () => {
      const blob = new Blob([JSON.stringify(window.__lastResults || {}, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'routes.json'; a.click();
      URL.revokeObjectURL(url);
    });

    bindKeyboard();
    bindLocateMe();
    bindBoostPanel();
    bindWeatherEvents();

    // Draw graph coverage bounding box so user knows where to click
    Api.getGraphBbox().then(data => {
      if (data && data.bbox) MapManager.drawGraphBbox(data.bbox);
    }).catch(() => {});

    Results.setSummary('Click inside the gold border to set Origin (A), then Destination (B)');
    refreshWeather();
    updateFindButton();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
