/* sidebar.js — form state, heuristic toggles, weight breakdown */
const Sidebar = (() => {
  // 22+ heuristics exposed in the UI (IDs must match backend ALL_HEURISTIC_IDS)
  const HEURISTICS_METADATA = [
    { id: 'weather',             icon: '⛅',  name: 'Weather',              kind: 'penalty' },
    { id: 'time_of_day',         icon: '⏰',  name: 'Time of day',          kind: 'penalty' },
    { id: 'vehicle_type',        icon: '🚗',  name: 'Vehicle type',         kind: 'neutral' },
    { id: 'intersection_density',icon: '🚦',  name: 'Intersection density', kind: 'penalty' },
    { id: 'surface',             icon: '🪨',  name: 'Surface quality',      kind: 'penalty' },
    { id: 'elevation',           icon: '⛰',   name: 'Elevation',            kind: 'penalty' },
    { id: 'safety',              icon: '🛡',  name: 'Safety',               kind: 'penalty' },
    { id: 'emission_zones',      icon: '🌱',  name: 'Emission zones',       kind: 'penalty' },
    { id: 'headway',             icon: '📏',  name: 'Headway',              kind: 'penalty' },
    { id: 'tram_tracks',         icon: '🚊',  name: 'Tram tracks',          kind: 'penalty' },
    { id: 'wind',                icon: '💨',  name: 'Wind',                 kind: 'penalty' },
    { id: 'parking',             icon: '🅿',  name: 'Parking',              kind: 'penalty' },
    { id: 'scenic',              icon: '🌿',  name: 'Scenic bonus',         kind: 'bonus'   },
    { id: 'school_zones',        icon: '🏫',  name: 'School zones',         kind: 'penalty' },
    { id: 'holiday_historical',  icon: '🎄',  name: 'Holiday traffic',      kind: 'penalty' },
    { id: 'events',              icon: '🎭',  name: 'Event closures',       kind: 'penalty' },
    { id: 'fiaker',              icon: '🐴',  name: 'Fiaker (horse cab)',   kind: 'penalty' },
    { id: 'snow_priority',       icon: '❄',   name: 'Snow priority',        kind: 'penalty' },
    { id: 'commuter_bridges',    icon: '🌉',  name: 'Commuter bridges',     kind: 'penalty' },
    { id: 'markets',             icon: '🛒',  name: 'Saturday markets',     kind: 'penalty' },
    { id: 'heuriger',            icon: '🍷',  name: 'Heuriger season',      kind: 'penalty' },
    { id: 'season',              icon: '🍂',  name: 'Season',               kind: 'penalty' },
    { id: 'lane_capacity',       icon: '🛣',  name: 'Lane capacity',        kind: 'penalty' },
    { id: 'road_works',          icon: '🚧',  name: 'Road works',           kind: 'penalty' },
    { id: 'humidity',            icon: '💧',  name: 'Humidity',             kind: 'penalty' },
    { id: 'visibility',          icon: '👁',  name: 'Visibility',           kind: 'penalty' },
    { id: 'pedestrian_density',  icon: '🚶',  name: 'Pedestrian density',   kind: 'penalty' },
    { id: 'delivery',            icon: '📦',  name: 'Delivery windows',     kind: 'penalty' },
    { id: 'nightnetwork',        icon: '🌙',  name: 'Night network',        kind: 'penalty' },
    { id: 'manual_adjustment',   icon: '✋',  name: 'Manual override',      kind: 'penalty' },
  ];

  const activated = new Set(HEURISTICS_METADATA.map(h => h.id));

  const state = {
    vehicle: 'car',
    profile: 'fastest',
    weather: 'clear',
    temperature: 15, humidity: 60, visibility_m: 5000,
    wind_speed: 3,   wind_deg: 180,
    hour: 12, minute: 0, day_of_week: 1, month: 4, date: todayISO(),
    useNow: true,
    advanced: false,
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

  /* ----- render heuristic list ----- */
  function renderHeuristicList() {
    const host = document.getElementById('heuristic-list');
    while (host.firstChild) host.removeChild(host.firstChild);

    HEURISTICS_METADATA.forEach(h => {
      const iconSpan = el('span', { cls: 'h-icon', text: h.icon });
      const nameSpan = el('span', { cls: 'h-name', text: h.name });
      const weightSpan = el('span', { cls: 'h-weight', text: activated.has(h.id) ? 'ON' : 'off' });
      const row = el('div',
        { cls: 'heuristic-item' + (activated.has(h.id) ? ' active' : ''), data: { id: h.id } },
        [iconSpan, nameSpan, weightSpan],
      );
      row.addEventListener('click', () => {
        if (activated.has(h.id)) activated.delete(h.id); else activated.add(h.id);
        row.classList.toggle('active');
        weightSpan.textContent = activated.has(h.id) ? 'ON' : 'off';
        updateHeuristicCount();
      });
      host.appendChild(row);
    });
    updateHeuristicCount();
  }

  function updateHeuristicCount() {
    const n = activated.size;
    document.getElementById('heuristic-count').textContent = String(n);
    document.getElementById('heuristic-sub-count').textContent =
      `${n} / ${HEURISTICS_METADATA.length} active`;
  }

  function bindEnableAllButtons() {
    document.getElementById('btn-enable-all').addEventListener('click', () => {
      HEURISTICS_METADATA.forEach(h => activated.add(h.id));
      renderHeuristicList();
    });
    document.getElementById('btn-disable-all').addEventListener('click', () => {
      activated.clear();
      renderHeuristicList();
    });
  }

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
    });
  }

  function bindAdvancedToggle() {
    const cb = document.getElementById('advanced-toggle');
    cb.addEventListener('change', () => {
      state.advanced = cb.checked;
      document.body.classList.toggle('advanced-mode', cb.checked);
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

  function bindTimeControls() {
    const useNow = document.getElementById('use-current-time');
    const dateInput = document.getElementById('input-date');
    const timeInput = document.getElementById('input-time');
    const slider = document.getElementById('hour-slider');
    const label = document.getElementById('time-label');

    function applyNow() {
      const now = new Date();
      state.date = now.toISOString().slice(0, 10);
      state.hour = now.getHours();
      state.minute = now.getMinutes();
      state.day_of_week = now.getDay();
      state.month = now.getMonth() + 1;
      dateInput.value = state.date;
      timeInput.value = `${String(state.hour).padStart(2,'0')}:${String(state.minute).padStart(2,'0')}`;
      slider.value = state.hour;
      updateTimeLabel();
    }
    function updateTimeLabel() {
      const dow = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][state.day_of_week];
      const isWeekend = state.day_of_week === 0 || state.day_of_week === 6;
      label.textContent =
        `${String(state.hour).padStart(2,'0')}:${String(state.minute).padStart(2,'0')} · ${dow}${isWeekend ? ' (Weekend)' : ''}`;
    }

    useNow.addEventListener('change', () => {
      state.useNow = useNow.checked;
      if (useNow.checked) applyNow();
    });
    dateInput.addEventListener('change', () => {
      state.useNow = false; useNow.checked = false;
      state.date = dateInput.value;
      const d = new Date(dateInput.value);
      state.day_of_week = d.getDay();
      state.month = d.getMonth() + 1;
      updateTimeLabel();
    });
    timeInput.addEventListener('change', () => {
      state.useNow = false; useNow.checked = false;
      const [h, m] = timeInput.value.split(':').map(Number);
      state.hour = h; state.minute = m;
      slider.value = h;
      updateTimeLabel();
    });
    slider.addEventListener('input', () => {
      state.useNow = false; useNow.checked = false;
      state.hour = parseInt(slider.value, 10);
      timeInput.value = `${String(state.hour).padStart(2,'0')}:00`;
      state.minute = 0;
      updateTimeLabel();
    });

    applyNow();
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
    return {
      start_lat: state.start[0], start_lon: state.start[1],
      goal_lat:  state.goal[0],  goal_lon:  state.goal[1],
      vehicle_type: state.vehicle,
      route_profile: state.profile,
      weather: state.weather,
      temperature: state.temperature,
      humidity: state.humidity,
      visibility_m: state.visibility_m,
      wind_speed: state.wind_speed,
      wind_deg: state.wind_deg,
      hour: state.hour, minute: state.minute,
      day_of_week: state.day_of_week, month: state.month,
      date: state.date,
      enabled_heuristics: Array.from(activated),
    };
  }

  function setStart(lat, lon) { state.start = [lat, lon]; }
  function setGoal (lat, lon) { state.goal  = [lat, lon]; }

  function init() {
    bindAdvancedToggle();
    bindCollapsibles();
    bindSelectorGroup('vehicle-selector', 'vehicle', 'vehicle');
    bindSelectorGroup('profile-selector', 'profile', 'profile');
    bindSelectorGroup('weather-selector', 'weather', 'weather');
    bindTimeControls();
    bindConditionSliders();
    renderHeuristicList();
    bindEnableAllButtons();
  }

  return {
    init, setStart, setGoal, buildRequest, state,
    HEURISTICS_METADATA, activated,
  };
})();
