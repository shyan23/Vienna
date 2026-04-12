/* overlays.js — toggleable map overlays (demo polygons / icons) */
const Overlays = (() => {
  let map = null;
  const layers = {};    // key -> L.LayerGroup
  const active = new Set();

  // static demo data (hand-placed Vienna points-of-interest)
  const DEMO = {
    schools: [
      [48.2020, 16.3685, 'Schule Rudolfsplatz'],
      [48.2135, 16.3602, 'Volksschule Alser'],
      [48.1910, 16.3540, 'BG Wiedner Gürtel'],
      [48.2248, 16.4162, 'Schule Donaustadt'],
    ],
    hotspots: [
      [48.2084, 16.3731, 'Stephansdom'],
      [48.2036, 16.3601, 'Schönbrunn hinweis'],
      [48.2065, 16.3627, 'MuseumsQuartier'],
      [48.2108, 16.3634, 'Hofburg'],
      [48.2168, 16.3608, 'Rathaus'],
    ],
    markets: [
      [48.1980, 16.3627, 'Naschmarkt'],
      [48.2110, 16.3640, 'Karmelitermarkt'],
      [48.2260, 16.4040, 'Viktor-Adler-Markt'],
    ],
    events: [
      [48.2168, 16.3608, 'Rathausplatz'],
      [48.2178, 16.4090, 'Donauinsel'],
      [48.1920, 16.3850, 'Prater-Hauptallee'],
    ],
    roadworks: [
      [48.2020, 16.3750],
      [48.2150, 16.3550],
      [48.2065, 16.3400],
    ],
    scenic: [
      [48.1855, 16.3180, 'Wienerwald corridor'],
      [48.2380, 16.3540, 'Kahlenberg ridge'],
      [48.1920, 16.4075, 'Prater allee'],
    ],
  };

  // semi-transparent traffic heatmap — evenly sampled across central districts
  const TRAFFIC_POINTS = [];
  for (let i = 0; i < 80; i++) {
    const lat = 48.18 + Math.random() * 0.08;
    const lon = 16.30 + Math.random() * 0.12;
    const intensity = Math.random();
    TRAFFIC_POINTS.push([lat, lon, intensity]);
  }

  function circleIcon(color, emoji) {
    return L.divIcon({
      html: null, className: 'ovl-icon',
      iconSize: [28, 28],
    });
  }

  function makeLabelMarker(lat, lon, color, emoji, label) {
    const marker = L.circleMarker([lat, lon], {
      radius: 9,
      fillColor: color,
      color: '#0b0f14',
      weight: 2,
      fillOpacity: 0.85,
    });
    if (label) marker.bindTooltip(label, { direction: 'top', className: 'ovl-tooltip' });
    return marker;
  }

  function buildLayers() {
    // Traffic (red→green heat circles)
    layers.traffic = L.layerGroup(
      TRAFFIC_POINTS.map(([lat, lon, i]) => {
        const color = i > 0.66 ? '#ff4d4d' : i > 0.33 ? '#ffb86c' : '#48c78e';
        return L.circle([lat, lon], {
          radius: 120 + i * 80,
          color, weight: 0,
          fillColor: color,
          fillOpacity: 0.25,
        });
      }),
    );

    layers.schools = L.layerGroup(
      DEMO.schools.map(([lat, lon, name]) => makeLabelMarker(lat, lon, '#ffcc66', '🏫', name)),
    );
    layers.hotspots = L.layerGroup(
      DEMO.hotspots.map(([lat, lon, name]) => makeLabelMarker(lat, lon, '#b794f4', '🏛', name)),
    );
    layers.markets = L.layerGroup(
      DEMO.markets.map(([lat, lon, name]) => makeLabelMarker(lat, lon, '#ff6b6b', '🛒', name)),
    );
    layers.events = L.layerGroup(
      DEMO.events.map(([lat, lon, name]) => makeLabelMarker(lat, lon, '#e056a0', '🎭', name)),
    );
    layers.roadworks = L.layerGroup(
      DEMO.roadworks.map(([lat, lon]) => L.circle([lat, lon], {
        radius: 140, color: '#ffb86c', weight: 2, dashArray: '6 4',
        fillColor: '#ffb86c', fillOpacity: 0.15,
      })),
    );
    layers.scenic = L.layerGroup(
      DEMO.scenic.map(([lat, lon, name]) => makeLabelMarker(lat, lon, '#48c78e', '🌿', name)),
    );
    // Snow: large soft circles over higher districts (Kahlenberg etc.)
    layers.snow = L.layerGroup([
      L.circle([48.2580, 16.3500], { radius: 900, color: '#6ea8fe', fillColor: '#6ea8fe', fillOpacity: 0.12, weight: 1 }),
      L.circle([48.2420, 16.3100], { radius: 800, color: '#6ea8fe', fillColor: '#6ea8fe', fillOpacity: 0.12, weight: 1 }),
    ]);
    // Wind arrow (single marker at city centre for now)
    layers.wind = L.layerGroup([
      L.marker([48.21, 16.37], {
        icon: L.divIcon({
          className: 'wind-arrow',
          html: null,
          iconSize: [40, 40],
        }),
      }),
    ]);
  }

  function init(leafletMap) {
    map = leafletMap;
    buildLayers();

    const controls = document.getElementById('overlay-controls');
    if (controls) {
      controls.addEventListener('click', (ev) => {
        const btn = ev.target.closest('[data-overlay]');
        if (!btn) return;
        const key = btn.dataset.overlay;
        toggle(key, btn);
      });
    }
  }

  function toggle(key, btn) {
    if (!layers[key]) return;
    if (active.has(key)) {
      map.removeLayer(layers[key]);
      active.delete(key);
      btn && btn.classList.remove('active');
    } else {
      layers[key].addTo(map);
      active.add(key);
      btn && btn.classList.add('active');
    }
  }

  return { init, toggle };
})();
