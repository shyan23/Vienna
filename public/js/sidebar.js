/* sidebar.js — form state, vehicle/weather/conditions */
const Sidebar = (() => {

  const state = {
    vehicle: 'car',
    weather: 'clear',
    temperature: 15, humidity: 60, visibility_m: 5000,
    wind_speed: 3,   wind_deg: 180,
    hour: new Date().getHours(), minute: new Date().getMinutes(),
    day_of_week: new Date().getDay(), month: new Date().getMonth() + 1,
    date: todayISO(),
    start: null, goal: null,
  };

  function todayISO() {
    return new Date().toISOString().slice(0, 10);
  }

  /* ----- safe DOM helper ----- */
  function el(tag, opts, children) {
    const e = document.createElement(tag);
    if (opts) {
      if (opts.cls)  e.className = opts.cls;
      if (opts.text !== undefined) e.textContent = opts.text;
      if (opts.data) for (const k in opts.data) e.dataset[k] = opts.data[k];
      if (opts.attrs) for (const k in opts.attrs) e.setAttribute(k, opts.attrs[k]);
    }
    if (children) for (const c of children) if (c) e.appendChild(c);
    return e;
  }


  const WEATHER_CAPTIONS = {
    clear:        '×1.00 — No penalty. Base Haversine distance only. Click Find Routes to compare.',
    cloudy:       '×1.10 — Mild overcast slowdown on all roads. Click Find Routes to activate.',
    fog:          '×1.30 + visibility penalty. Roads under 3 km sight penalized. Click Find Routes to activate.',
    light_rain:   '×1.25 — Cyclists, walkers & e-scooters get ×1.30 extra penalty. Click Find Routes to activate.',
    rain:         '×1.50 — Tram track edges become ×1.70 for cyclists in wet. Click Find Routes to activate.',
    thunderstorm: '×1.60 base — Walkers ×2.30, cyclists ×2.20. Heaviest exposed-vehicle penalty. Click Find Routes to activate.',
    light_snow:   '×1.40 — Snow priority heuristic activates. Non-priority roads penalized ×1.60. Click Find Routes to activate.',
    heavy_snow:   '×1.80 — All snow penalties stack. Auto-infers black ice if temp < 2°C & humidity > 80%. Click Find Routes to activate.',
  };

  /* ----- vehicle/profile/weather selectors ----- */
  function bindSelectorGroup(containerId, attr, key) {
    const group = document.getElementById(containerId);
    if (!group) return;
    group.addEventListener('click', (ev) => {
      const btn = ev.target.closest(`[data-${attr}]`);
      if (!btn) return;
      group.querySelectorAll(`[data-${attr}]`).forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state[key] = btn.dataset[attr];
      if (attr === 'weather') {
        const cap = document.getElementById('weather-caption');
        if (cap) cap.textContent = WEATHER_CAPTIONS[btn.dataset[attr]] || '';
      }
    });
  }

  function bindCollapsibles() {
    document.querySelectorAll('.panel-header.collapsible').forEach(h => {
      h.addEventListener('click', () => {
        const body = document.getElementById(h.dataset.target);
        if (!body) return;
        body.classList.toggle('collapsed');
        h.classList.toggle('open');
      });
    });
  }

  function syncTimeFromNow() {
    const now = new Date();
    state.hour = now.getHours();
    state.minute = now.getMinutes();
    state.day_of_week = now.getDay();
    state.month = now.getMonth() + 1;
    state.date = now.toISOString().slice(0, 10);
  }

  function bindConditionSliders() {
    const bindings = [
      ['temp-slider', 'temp-val', 'temperature',  v => `${v}°C`],
      ['humidity-slider','humidity-val','humidity', v => `${v}%`],
      ['visibility-slider','visibility-val','visibility_m', v => `${(v/1000).toFixed(1)} km`],
      ['wind-slider','wind-val','wind_speed', v => `${v} m/s`],
    ];
    bindings.forEach(([sid, vid, key, fmt]) => {
      const s = document.getElementById(sid);
      const l = document.getElementById(vid);
      if (!s || !l) return;
      s.addEventListener('input', () => {
        const v = Number(s.value);
        state[key] = v;
        l.textContent = fmt(v);
      });
    });
  }

  function buildRequest() {
    if (!state.start || !state.goal) return null;
    syncTimeFromNow();
    return {
      start_lat: state.start[0], start_lon: state.start[1],
      goal_lat:  state.goal[0],  goal_lon:  state.goal[1],
      vehicle_type: state.vehicle,
      weather: state.weather,
      temperature: state.temperature,
      humidity: state.humidity,
      visibility_m: state.visibility_m,
      wind_speed: state.wind_speed,
      wind_deg: state.wind_deg,
      hour: state.hour, minute: state.minute,
      day_of_week: state.day_of_week, month: state.month,
      date: state.date,
      enabled_heuristics: [],
    };
  }

  function setStart(lat, lon) { state.start = [lat, lon]; }
  function setGoal (lat, lon) { state.goal  = [lat, lon]; }

  function init() {
    bindCollapsibles();
    bindSelectorGroup('vehicle-selector', 'vehicle', 'vehicle');
    bindSelectorGroup('weather-selector', 'weather', 'weather');
    bindConditionSliders();
    // Always advanced mode — make all advanced-only panels visible
    document.body.classList.add('advanced-mode');
    // Set initial caption for default weather (clear)
    const cap = document.getElementById('weather-caption');
    if (cap) cap.textContent = WEATHER_CAPTIONS[state.weather] || '';
  }

  return {
    init, setStart, setGoal, buildRequest, state,
  };
})();
