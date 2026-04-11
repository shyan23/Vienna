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
    showLoading(true, 'Computing 8 algorithms…');
    Results.setSummary('Running…');
    try {
      const t0 = performance.now();
      const resp = await Api.findPath(req);
      const dt = (performance.now() - t0).toFixed(0);
      window.__lastResults = resp.results || {};
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

  function onClear() {
    MapManager.clearMarkers();
    MapManager.clearRoutes();
    Sidebar.setStart(null, null); Sidebar.state.start = null;
    Sidebar.setGoal(null, null);  Sidebar.state.goal  = null;
    document.getElementById('input-start').value = '';
    document.getElementById('input-goal').value = '';
    document.getElementById('start-coords').textContent = '';
    document.getElementById('goal-coords').textContent = '';
    Results.render({});
    Results.setSummary('Click the map to set Origin (A) and Destination (B)');
    updateFindButton();
  }

  function bindKeyboard() {
    document.addEventListener('keydown', (ev) => {
      if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA') return;
      if (ev.key === 'Enter') onFindRoutes();
      else if (ev.key === 'Escape') onClear();
      else if (ev.key === 'a' || ev.key === 'A') {
        const cb = document.getElementById('advanced-toggle');
        cb.checked = !cb.checked; cb.dispatchEvent(new Event('change'));
      }
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

  function init() {
    Sidebar.init();
    const map = MapManager.init('map', { center: VIENNA_CENTER, zoom: 13 });
    Overlays.init(map);
    Results.init();
    Explainer.init();
    Presets.init();

    MapManager.onStart((lat, lon) => {
      Sidebar.setStart(lat, lon);
      document.getElementById('input-start').value = fmtCoord(lat, lon);
      document.getElementById('start-coords').textContent = fmtCoord(lat, lon);
      updateFindButton();
    });
    MapManager.onGoal((lat, lon) => {
      Sidebar.setGoal(lat, lon);
      document.getElementById('input-goal').value = fmtCoord(lat, lon);
      document.getElementById('goal-coords').textContent = fmtCoord(lat, lon);
      updateFindButton();
    });

    Results.onRowClickHandler((key) => MapManager.selectRoute(key));

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

    Results.setSummary('Click the map to set Origin (A), then Destination (B)');
    refreshWeather();
    updateFindButton();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
