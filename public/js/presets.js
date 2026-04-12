/* presets.js — scenario buttons that apply traffic overrides + weather state */
const Presets = (() => {
  const PRESETS = [
    {
      id: 'marathon', icon: '🏃‍♂', name: 'Vienna Marathon',
      desc: 'Ringstraße fully closed — all Ring roads blocked',
      patch: { weather: 'clear', vehicle: 'car' },
      // Block all Ringstraße edges (resolved at activation time)
      trafficAction: 'marathon',
    },
    {
      id: 'blizzard', icon: '❄', name: 'Blizzard',
      desc: 'Winter storm — 2 random roads blocked',
      patch: { weather: 'heavy_snow', vehicle: 'car' },
      trafficAction: 'blizzard',
    },
    {
      id: 'christmas', icon: '🎄', name: 'Christmas Market',
      desc: 'December evening — heavy traffic on 2 central roads',
      patch: { weather: 'cloudy', vehicle: 'car' },
      trafficAction: 'christmas',
    },
  ];

  // Ring road street names (marathon blocks all of these)
  const RING_NAMES = [
    'Schottenring', 'Universitätsring', 'Kärntner Ring',
    'Opernring', 'Schubertring', 'Burgring', 'Parkring',
    'Franz-Josefs-Kai',
  ];

  function applyPatch(patch) {
    for (const [k, v] of Object.entries(patch)) {
      if (k === 'vehicle' || k === 'weather') {
        const selGroupId = k === 'vehicle' ? 'vehicle-selector' : 'weather-selector';
        const group = document.getElementById(selGroupId);
        if (group) {
          group.querySelectorAll('[data-' + k + ']').forEach(function (b) { b.classList.remove('active'); });
          var target = group.querySelector('[data-' + k + '="' + v + '"]');
          if (target) target.classList.add('active');
        }
      }
      Sidebar.state[k] = v;
    }
  }

  function el(tag, opts, children) {
    var e = document.createElement(tag);
    if (opts) {
      if (opts.cls) e.className = opts.cls;
      if (opts.text !== undefined) e.textContent = opts.text;
    }
    if (children) for (var i = 0; i < children.length; i++) e.appendChild(children[i]);
    return e;
  }

  async function activateScenario(preset) {
    // 1. Clear previous overrides
    await Api.clearOverrides();

    // 2. Apply sidebar state (weather, vehicle)
    applyPatch(preset.patch);

    // 3. Apply traffic overrides based on scenario type
    var overrides = [];

    if (preset.trafficAction === 'marathon') {
      // Fetch all ring road edges from the backend and block them
      overrides = await getEdgesByStreetName(RING_NAMES, 100);
    } else if (preset.trafficAction === 'blizzard') {
      // Block 2 random roads from last results (or random graph edges)
      overrides = await getRandomOverrides(2, 100);
    } else if (preset.trafficAction === 'christmas') {
      // Heavy traffic on 2 random central roads
      overrides = await getRandomOverrides(2, 85);
    }

    // 4. Send overrides to the server
    for (var i = 0; i < overrides.length; i++) {
      await Api.setOverride(overrides[i].edge_id, overrides[i].intensity);
    }

    // 5. Notify app.js about the overrides so the info panel and map update
    if (window.__onScenarioApplied) {
      window.__onScenarioApplied(overrides, preset);
    }
  }

  async function getEdgesByStreetName(streetNames, intensity) {
    // Fetch from a new API endpoint that returns edge_ids by street name
    var result = [];
    try {
      var data = await Api.getEdgesByName(streetNames);
      for (var i = 0; i < data.length; i++) {
        result.push({ edge_id: data[i], intensity: intensity });
      }
    } catch (e) {
      console.warn('Failed to fetch ring edges:', e);
    }
    return result;
  }

  function getRandomOverrides(count, intensity) {
    var results = window.__lastResults || {};
    var allPaths = [];
    var entries = Object.values(results);
    for (var i = 0; i < entries.length; i++) {
      var r = entries[i];
      if (r && r.path_node_ids && r.path_node_ids.length > 1) {
        allPaths.push(r.path_node_ids);
      }
    }
    var overrides = [];
    if (allPaths.length === 0) return overrides;
    var used = {};
    for (var j = 0; j < count; j++) {
      var path = allPaths[Math.floor(Math.random() * allPaths.length)];
      var idx = Math.floor(Math.random() * (path.length - 1));
      var eid = path[idx] + '_' + path[idx + 1];
      if (!used[eid]) {
        used[eid] = true;
        overrides.push({ edge_id: eid, intensity: intensity });
        // Also reverse direction
        var rev = path[idx + 1] + '_' + path[idx];
        overrides.push({ edge_id: rev, intensity: intensity });
      }
    }
    return overrides;
  }

  function render() {
    var host = document.getElementById('preset-grid');
    while (host.firstChild) host.removeChild(host.firstChild);
    PRESETS.forEach(function (p) {
      var iconEl = el('span', { cls: 'preset-icon', text: p.icon });
      var nameEl = el('div', { text: p.name });
      var descEl = el('div', { cls: 'muted small', text: p.desc });
      var btn = el('button', { cls: 'preset-btn' }, [iconEl, nameEl, descEl]);
      btn.addEventListener('click', function () { activateScenario(p); });
      host.appendChild(btn);
    });
  }

  function init() { render(); }

  return { init, PRESETS, activateScenario };
})();
