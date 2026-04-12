/* api.js — thin fetch wrapper around the FastAPI backend */
const Api = (() => {
  const BASE = window.location.origin;

  async function post(path, body) {
    const res = await fetch(BASE + '/api' + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    if (!res.ok) throw new Error(`POST ${path} → ${res.status}: ${await res.text()}`);
    return res.json();
  }
  async function get(path) {
    const res = await fetch(BASE + '/api' + path);
    if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
    return res.json();
  }
  async function del(path) {
    const res = await fetch(BASE + '/api' + path, { method: 'DELETE' });
    if (!res.ok) throw new Error(`DELETE ${path} → ${res.status}`);
    return res.json();
  }

  return {
    findPath:       (req)              => post('/find-path', req),
    getWeather:     ()                 => get('/weather'),
    setOverride:    (edgeId, intensity)=> post('/manual-override', { edge_id: edgeId, intensity }),
    clearOverrides: ()                 => del('/manual-override'),
    getGraphStats:  ()                 => get('/graph/stats'),
    getGraphBbox:   ()                 => get('/graph/bbox'),
    getGraphNodes:  ()                 => get('/graph/nodes'),
    getEdgeNames:   (edgeIds)          => post('/graph/edge-names', { edge_ids: edgeIds }),
    getEvents:      (date)             => get(`/events/${date}`),
    health:         ()                 => get('/health'),
  };
})();
