/* presets.js — scenario buttons that bulk-patch the sidebar state */
const Presets = (() => {
  const PRESETS = [
    {
      id: 'marathon', icon: '🏃‍♂', name: 'Vienna Marathon',
      desc: 'Early April Sunday — Ringstraße closed',
      patch: {
        date: '2026-04-12', hour: 9, minute: 0, day_of_week: 0, month: 4,
        vehicle: 'car', profile: 'fastest', weather: 'clear',
      },
    },
    {
      id: 'blizzard', icon: '❄', name: 'Blizzard',
      desc: 'Winter storm — reduced visibility',
      patch: {
        date: '2026-01-15', hour: 8, minute: 0, day_of_week: 4, month: 1,
        vehicle: 'car', profile: 'safest', weather: 'heavy_snow',
        temperature: -5, humidity: 90, visibility_m: 300, wind_speed: 18,
      },
    },
    {
      id: 'christmas', icon: '🎄', name: 'Christmas market',
      desc: 'December evening — centre jammed',
      patch: {
        date: '2026-12-10', hour: 19, minute: 0, day_of_week: 4, month: 12,
        vehicle: 'car', profile: 'fastest', weather: 'cloudy',
        temperature: 2, humidity: 75,
      },
    },
    {
      id: 'bike_rain', icon: '🚴', name: 'Bike in rain',
      desc: 'Commute on a wet morning',
      patch: {
        hour: 8, minute: 15,
        vehicle: 'bicycle', profile: 'safest', weather: 'rain',
        temperature: 10, humidity: 88, visibility_m: 2000,
      },
    },
    {
      id: 'heuriger', icon: '🍷', name: 'Heuriger evening',
      desc: 'Grinzing wine-tavern trip',
      patch: {
        date: '2026-09-12', hour: 19, minute: 0, day_of_week: 6, month: 9,
        vehicle: 'taxi', profile: 'fastest', weather: 'clear', temperature: 18,
      },
    },
    {
      id: 'late_walk', icon: '🌙', name: 'Late-night walk',
      desc: 'Safest walking after midnight',
      patch: {
        hour: 1, minute: 30,
        vehicle: 'walking', profile: 'safest', weather: 'clear',
        temperature: 12, humidity: 70,
      },
    },
    {
      id: 'donauinsel', icon: '🎪', name: 'Donauinselfest',
      desc: 'June festival — crowded riverbanks',
      patch: {
        date: '2026-06-26', hour: 18, minute: 0, day_of_week: 5, month: 6,
        vehicle: 'metro', profile: 'fastest', weather: 'clear', temperature: 26,
      },
    },
  ];

  function applyPatch(patch) {
    for (const [k, v] of Object.entries(patch)) {
      if (k === 'vehicle' || k === 'profile' || k === 'weather') {
        const selGroupId =
          k === 'vehicle' ? 'vehicle-selector' :
          k === 'profile' ? 'profile-selector' : 'weather-selector';
        const group = document.getElementById(selGroupId);
        if (group) {
          group.querySelectorAll(`[data-${k}]`).forEach(b => b.classList.remove('active'));
          const target = group.querySelector(`[data-${k}="${v}"]`);
          if (target) target.classList.add('active');
        }
      }
      Sidebar.state[k] = v;
    }
    // Re-sync visible inputs
    const dateInput = document.getElementById('input-date');
    const timeInput = document.getElementById('input-time');
    const hourSlider = document.getElementById('hour-slider');
    if (patch.date)  dateInput.value = patch.date;
    if (patch.hour != null) {
      timeInput.value = `${String(patch.hour).padStart(2,'0')}:${String(patch.minute||0).padStart(2,'0')}`;
      hourSlider.value = patch.hour;
    }
    // Also refresh the label manually
    const label = document.getElementById('time-label');
    const dow = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][Sidebar.state.day_of_week];
    label.textContent =
      `${String(Sidebar.state.hour).padStart(2,'0')}:${String(Sidebar.state.minute).padStart(2,'0')} · ${dow}`;
    document.getElementById('use-current-time').checked = false;
    Sidebar.state.useNow = false;

    // Sync condition sliders if present
    const syncSlider = (id, valId, val, fmt) => {
      if (val == null) return;
      const s = document.getElementById(id);
      const l = document.getElementById(valId);
      if (s) s.value = val;
      if (l) l.textContent = fmt(val);
    };
    syncSlider('temp-slider','temp-val', patch.temperature,   v => `${v}°C`);
    syncSlider('humidity-slider','humidity-val', patch.humidity, v => `${v}%`);
    syncSlider('visibility-slider','visibility-val', patch.visibility_m, v => `${(v/1000).toFixed(1)} km`);
    syncSlider('wind-slider','wind-val', patch.wind_speed, v => `${v} m/s`);
  }

  function el(tag, opts, children) {
    const e = document.createElement(tag);
    if (opts) {
      if (opts.cls)  e.className = opts.cls;
      if (opts.text !== undefined) e.textContent = opts.text;
    }
    if (children) for (const c of children) e.appendChild(c);
    return e;
  }

  function render() {
    const host = document.getElementById('preset-grid');
    while (host.firstChild) host.removeChild(host.firstChild);
    PRESETS.forEach(p => {
      const iconEl = el('span', { cls: 'preset-icon', text: p.icon });
      const nameEl = el('div', { text: p.name });
      const descEl = el('div', { cls: 'muted small', text: p.desc });
      const btn = el('button', { cls: 'preset-btn' }, [iconEl, nameEl, descEl]);
      btn.addEventListener('click', () => applyPatch(p.patch));
      host.appendChild(btn);
    });
  }

  function init() { render(); }

  return { init, PRESETS, applyPatch };
})();
