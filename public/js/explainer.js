/* explainer.js — modal walking through each algorithm's characteristics */
const Explainer = (() => {
  let currentIndex = 0;
  let algoKeys = [];
  let allResults = {};

  const ALGO_INFO = {
    bfs: {
      name: 'Breadth-First Search (BFS)',
      emoji: '🌊',
      desc: 'Explores nodes layer by layer from the start. Finds the path with the fewest hops — NOT the shortest in metres.',
      optimal: 'Optimal only for unit edge costs.',
      complexity: 'Time O(V+E), space O(V). Queue-based frontier.',
      useWhen: 'Useful when you care about minimum number of intersections rather than distance.',
    },
    dfs: {
      name: 'Depth-First Search (DFS)',
      emoji: '🕳',
      desc: 'Follows one branch until it dead-ends, then backtracks. Produces *some* path, not a good one.',
      optimal: 'Non-optimal. Included as a baseline.',
      complexity: 'Time O(V+E), space O(h) where h is max depth.',
      useWhen: 'Shows how much worse an uninformed algorithm can be.',
    },
    ucs: {
      name: 'Uniform-Cost Search (UCS)',
      emoji: '⚖',
      desc: 'Expands frontier by cheapest path-cost. Equivalent to Dijkstra from a single source.',
      optimal: 'Optimal on non-negative edge weights.',
      complexity: 'Time O(E log V) with a binary heap.',
      useWhen: 'When you have no useful heuristic. Same guarantees as Dijkstra.',
    },
    dijkstra: {
      name: 'Dijkstra',
      emoji: '🎯',
      desc: 'Single-source shortest path using a priority queue. Our *ground truth* for optimality comparisons.',
      optimal: 'Optimal on non-negative weights — we measure all other algorithms against its distance.',
      complexity: 'Time O((V+E) log V).',
      useWhen: 'Always, when the heuristic is unknown or distrusted.',
    },
    greedy: {
      name: 'Greedy Best-First',
      emoji: '🏃',
      desc: 'Expands the node that *looks* closest to the goal (pure h). Fast but short-sighted.',
      optimal: 'Not optimal — can take long detours.',
      complexity: 'Time O(E), space O(V).',
      useWhen: 'When you need speed and any path is acceptable.',
    },
    astar: {
      name: 'A*',
      emoji: '⭐',
      desc: 'f(n) = g(n) + h(n). Combines path cost and heuristic for optimal + efficient search.',
      optimal: 'Optimal when h is admissible (never overestimates). Our composite heuristic is capped to stay ε-admissible.',
      complexity: 'Time depends on heuristic quality — typically much smaller than Dijkstra.',
      useWhen: 'The workhorse. Use whenever you have a reasonable heuristic.',
    },
    weighted_astar: {
      name: 'Weighted A*',
      emoji: '⚡',
      desc: 'f(n) = g(n) + ε·h(n). Sacrifices optimality for speed — bounded-suboptimal by factor ε.',
      optimal: 'Suboptimal by at most ε (we default ε=1.5, so ≤50% above optimal).',
      complexity: 'Usually 2-5× faster than A*.',
      useWhen: 'Interactive routing where speed > a few percent of optimality.',
    },
    bidirectional_astar: {
      name: 'Bidirectional A*',
      emoji: '🔀',
      desc: 'Searches forward from start AND backward from goal. Meet-in-the-middle cuts branching factor.',
      optimal: 'Optimal with admissible heuristics and proper termination (we track best_sum).',
      complexity: 'Often ~2× faster than one-way A* on long routes.',
      useWhen: 'Long routes across the city where two frontiers can meet quickly.',
    },
  };

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

  function open(results) {
    allResults = results || {};
    algoKeys = Object.keys(ALGO_INFO);
    currentIndex = 0;
    renderTabs();
    renderBody();
    document.getElementById('explainer-modal').classList.remove('hidden');
  }
  function close() {
    document.getElementById('explainer-modal').classList.add('hidden');
  }

  function renderTabs() {
    const host = document.getElementById('explainer-tabs');
    while (host.firstChild) host.removeChild(host.firstChild);
    algoKeys.forEach((k, i) => {
      const info = ALGO_INFO[k];
      const tab = el('div', {
        cls: 'modal-tab' + (i === currentIndex ? ' active' : ''),
        text: `${info.emoji} ${Results.ALGO_DISPLAY[k] || k}`,
      });
      tab.addEventListener('click', () => { currentIndex = i; renderTabs(); renderBody(); });
      host.appendChild(tab);
    });
  }

  function renderBody() {
    const host = document.getElementById('explainer-body');
    while (host.firstChild) host.removeChild(host.firstChild);
    const key = algoKeys[currentIndex];
    const info = ALGO_INFO[key];
    const r = allResults[key];

    host.appendChild(el('h4', { text: `${info.emoji} ${info.name}` }));
    host.appendChild(el('p', { text: info.desc }));

    host.appendChild(el('h4', { text: 'Optimality' }));
    host.appendChild(el('p', { text: info.optimal }));

    host.appendChild(el('h4', { text: 'Complexity' }));
    host.appendChild(el('p', { text: info.complexity }));

    host.appendChild(el('h4', { text: 'When to use' }));
    host.appendChild(el('p', { text: info.useWhen }));

    if (r) {
      host.appendChild(el('h4', { text: 'Run on the current route' }));
      if (r.error) {
        host.appendChild(el('p', { text: `Error: ${r.error}` }));
      } else {
        const lines = [
          `distance = ${(r.distance_m/1000).toFixed(2)} km`,
          `time     = ${Math.round(r.estimated_time_s)} s`,
          `nodes    = ${r.nodes_expanded}`,
          `compute  = ${(r.compute_time_ms || 0).toFixed(2)} ms`,
          `gap      = ${r.optimality_gap_pct != null ? r.optimality_gap_pct.toFixed(2) + '%' : '—'}`,
        ];
        const code = el('p');
        lines.forEach((t, i) => {
          const c = el('code', { text: t });
          code.appendChild(c);
          if (i < lines.length - 1) code.appendChild(el('br'));
        });
        host.appendChild(code);
      }
    }
  }

  function init() {
    document.getElementById('btn-explainer').addEventListener('click', () => open(window.__lastResults || {}));
    document.getElementById('btn-modal-close').addEventListener('click', close);
    document.getElementById('modal-backdrop').addEventListener('click', close);
    document.getElementById('btn-explainer-prev').addEventListener('click', () => {
      if (currentIndex > 0) { currentIndex--; renderTabs(); renderBody(); }
    });
    document.getElementById('btn-explainer-next').addEventListener('click', () => {
      if (currentIndex < algoKeys.length - 1) { currentIndex++; renderTabs(); renderBody(); }
    });
  }

  return { init, open, close };
})();
