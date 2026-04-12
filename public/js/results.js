/* results.js — results table rendering, sorting, row selection */
const Results = (() => {
  const ALGO_DISPLAY = {
    bfs:                 'BFS',
    dfs:                 'DFS',
    ucs:                 'Uniform-Cost',
    dijkstra:            'Dijkstra',
    greedy:              'Greedy Best-First',
    astar:               'A*',
    weighted_astar:      'Weighted A*',
    bidirectional_astar: 'Bidirectional A*',
  };

  let current = {};          // key -> PathResult dict
  let sortKey = 'distance';
  let selectedKey = null;
  let onRowClick = null;

  function el(tag, opts, children) {
    const e = document.createElement(tag);
    if (opts) {
      if (opts.cls)  e.className = opts.cls;
      if (opts.text !== undefined) e.textContent = opts.text;
      if (opts.data) for (const k in opts.data) e.dataset[k] = opts.data[k];
    }
    if (children) for (const c of children) if (c) e.appendChild(c);
    return e;
  }

  function fmtMeters(m) {
    if (m == null) return '—';
    return m >= 1000 ? `${(m/1000).toFixed(2)} km` : `${Math.round(m)} m`;
  }
  function fmtSeconds(s) {
    if (s == null) return '—';
    if (s < 60) return `${Math.round(s)} s`;
    if (s < 3600) return `${Math.floor(s/60)}m ${Math.round(s%60)}s`;
    return `${Math.floor(s/3600)}h ${Math.round((s%3600)/60)}m`;
  }
  function fmtMs(ms) {
    if (ms == null) return '—';
    return ms < 1 ? `${(ms*1000).toFixed(0)} µs` : ms < 100 ? `${ms.toFixed(1)} ms` : `${Math.round(ms)} ms`;
  }
  function fmtGap(gap) {
    if (gap == null || isNaN(gap)) return '—';
    if (gap < 0.01) return 'optimal';
    return `+${gap.toFixed(1)}%`;
  }

  function render(results) {
    current = results || {};
    const tbody = document.getElementById('results-tbody');
    while (tbody.firstChild) tbody.removeChild(tbody.firstChild);

    const entries = Object.entries(current);
    if (entries.length === 0) {
      tbody.appendChild(el('tr', null, [el('td', { text: 'No results', attrs: { colspan: 6 } })]));
      return;
    }

    // Sort
    entries.sort(([, a], [, b]) => {
      const va = pickSortVal(a, sortKey);
      const vb = pickSortVal(b, sortKey);
      return va - vb;
    });

    for (const [key, r] of entries) {
      const algoLabel = ALGO_DISPLAY[key] || key;
      const color = (window.MapManager && MapManager.ALGO_COLORS[key]) || '#6ea8fe';

      const swatch = el('span', { cls: 'algo-swatch' });
      swatch.style.background = color;
      const nameSpan = el('span', { cls: 'algo-name', text: algoLabel });
      const algoCell = el('td', { cls: 'algo-cell' }, [swatch, nameSpan]);
      if (r.is_optimal) algoCell.appendChild(el('span', { cls: 'optimal-star', text: ' ★' }));

      const row = el('tr', { data: { key } }, [
        algoCell,
        el('td', { text: r.error ? '—' : fmtMeters(r.distance_m) }),
        el('td', { text: r.error ? '—' : fmtSeconds(r.estimated_time_s) }),
        el('td', { cls: 'col-nodes', text: r.error ? '—' : String(r.nodes_expanded ?? '—') }),
        el('td', { cls: 'col-compute', text: r.error ? '—' : fmtMs(r.compute_time_ms) }),
      ]);
      if (r.error) row.classList.add('error-row');
      if (selectedKey === key) row.classList.add('selected');
      row.addEventListener('click', () => {
        selectedKey = key;
        document.querySelectorAll('#results-tbody tr').forEach(tr => tr.classList.remove('selected'));
        row.classList.add('selected');
        onRowClick && onRowClick(key, r);
      });
      tbody.appendChild(row);
    }

    updateHeader();
  }

  function pickSortVal(r, k) {
    if (!r || r.error) return Infinity;
    if (k === 'distance') return r.distance_m ?? Infinity;
    if (k === 'time')     return r.estimated_time_s ?? Infinity;
    if (k === 'nodes')    return r.nodes_expanded ?? Infinity;
    if (k === 'compute')  return r.compute_time_ms ?? Infinity;
    return 0;
  }

  function updateHeader() {
    const valid = Object.values(current).filter(r => r && !r.error);
    const meta = document.getElementById('results-meta');
    if (!valid.length) { meta.textContent = ''; return; }
    const best = valid.reduce((a, b) => (a.distance_m <= b.distance_m ? a : b));
    const avg = valid.reduce((s, r) => s + (r.distance_m || 0), 0) / valid.length;
    meta.textContent = `${valid.length}/8 succeeded · best ${fmtMeters(best.distance_m)} · avg ${fmtMeters(avg)}`;

    const footer = document.getElementById('results-footer-stats');
    const totalCompute = valid.reduce((s, r) => s + (r.compute_time_ms || 0), 0);
    footer.textContent = `total compute: ${fmtMs(totalCompute)} · nodes sum: ${valid.reduce((s, r) => s + (r.nodes_expanded || 0), 0)}`;
  }

  function setSort(key) {
    sortKey = key;
    document.querySelectorAll('.sort-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.sort === key);
    });
    render(current);
  }

  function bindSort() {
    document.querySelectorAll('.sort-btn').forEach(b => {
      b.addEventListener('click', () => setSort(b.dataset.sort));
    });
  }

  function bindDrawer() {
    const drawer = document.getElementById('results-drawer');
    const toggleBtn = document.getElementById('drawer-toggle');
    const handle = document.getElementById('drawer-handle');
    function toggle() {
      const collapsed = drawer.classList.toggle('collapsed');
      toggleBtn.textContent = collapsed ? '▲ Expand' : '▼ Collapse';
    }
    toggleBtn.addEventListener('click', (ev) => { ev.stopPropagation(); toggle(); });
    handle.addEventListener('click', toggle);
  }

  function setSummary(text) {
    document.getElementById('drawer-summary').textContent = text;
  }
  function expand() {
    const drawer = document.getElementById('results-drawer');
    drawer.classList.remove('collapsed');
    document.getElementById('drawer-toggle').textContent = '▼ Collapse';
  }

  function onRowClickHandler(fn) { onRowClick = fn; }

  function init() {
    bindSort();
    bindDrawer();
  }

  return { init, render, setSort, setSummary, expand, onRowClickHandler, ALGO_DISPLAY };
})();
