/* ==========================================================================
   Galene UI  —  Marine Intelligence
   POST /ask  ·  GET /health  ·  GET /geo/*  ·  Leaflet overlays

   DATA-INTEGRITY CONTRACT
   The backend's deterministic risk engine is the only source of verdicts.
   Nothing in this file computes, scales, converts or nudges a risk value.
   Values shown here are either returned verbatim by /ask, extracted verbatim
   from the backend's own answer text using its exact published templates, or
   read from the existing /geo/* endpoints. Anything absent is rendered as
   "Data unavailable" — never guessed.
   ========================================================================== */

'use strict';

/* ── Constants ──────────────────────────────────────────────────────── */

const VERDICTS = {
  safe: { label: 'SAFE', chip: 'verdict-chip--safe' },
  caution: { label: 'CAUTION', chip: 'verdict-chip--caution' },
  unsafe: { label: 'UNSAFE', chip: 'verdict-chip--unsafe' },
  info: { label: 'INFORMATIONAL', chip: 'verdict-chip--info' },
  unknown: { label: 'UNCLASSIFIED', chip: '' }
};

/* Canonical pipeline stages. Only stages the backend actually reports are
   rendered — nothing is invented to fill a gap. */
const PIPELINE = [
  { key: 'intent', name: 'Intent Classification', short: 'Intent',
    match: (s) => s.agent === 'planner' && String(s.tool || '').startsWith('classify:') },
  { key: 'planner', name: 'Planner / Orchestrator', short: 'Planner',
    match: (s) => s.agent === 'planner' && !String(s.tool || '').startsWith('classify:') },
  { key: 'weather', name: 'Weather & Hazard', short: 'Weather', match: (s) => s.agent === 'weather' },
  { key: 'ocean', name: 'Ocean Analytics', short: 'Ocean', match: (s) => s.agent === 'ocean' },
  { key: 'geo', name: 'Geospatial Reasoning', short: 'GIS', match: (s) => s.agent === 'geo' },
  { key: 'risk', name: 'Risk Engine', short: 'Risk', match: (s) => s.agent === 'risk' },
  { key: 'evidence', name: 'Evidence / RAG', short: 'Evidence', match: null },
  { key: 'response', name: 'Final Response', short: 'Response', match: (s) => s.agent === 'viz' }
];

/* Loading indicator. The backend streams no progress, so these stages are
   driven purely by elapsed time and are replaced by the real trace the moment
   the response lands. Purely a visual indicator — never a claim about which
   agent is actually running. */
const ANALYZE_STAGES = [
  'Understanding query', 'Planning analysis', 'Discovering marine data',
  'Analysing weather', 'Analysing ocean conditions',
  'Checking geospatial constraints', 'Assessing risk', 'Preparing evidence'
];
const STAGE_TIMING = [380, 880, 1500, 2300, 3200, 4300, 5600, 6600];

/* Exact templates published by backend/app/agents/risk.py. Anchored and
   strict: if the backend ever changes its wording, nothing is extracted. */
const RE_WIND = /^Wind\s+(-?[\d.]+)\s*km\/h\s+(exceeds unsafe limit|above caution limit|within limits)/i;
const RE_WAVE = /^Waves\s+(-?[\d.]+)\s*m\s+(exceeds unsafe limit|above caution limit|within limits)/i;
const RE_IMD = /^IMD warning:\s*(.+)$/i;
/* Exact templates published by planner.py (pfz / zone branches). */
const RE_PFZ_COUNT = /PFZ:\s*(\d+)\s+zone\(s\)/i;
const RE_SST = /SST\s+(-?[\d.]+)\s*C\b/;
const RE_CHL = /chlorophyll\s+(-?[\d.]+)\s*mg\/m3/i;
/* Target window, as emitted by weather.summarize() / planner.py. */
const RE_WINDOW = /Window\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s*[-–—]\s*(\d{2}:\d{2})/;
const RE_SNAPSHOT = /Live snapshot\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s*[-–—]\s*(\d{2}:\d{2})/;

const NA = 'Data unavailable';

/* ── DOM helpers ────────────────────────────────────────────────────── */

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};
const esc = (v) => String(v == null ? '' : v)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const fmtPoint = (la, lo) =>
  Math.abs(la).toFixed(2) + '° ' + (la >= 0 ? 'N' : 'S') + ', ' +
  Math.abs(lo).toFixed(2) + '° ' + (lo >= 0 ? 'E' : 'W');
const fmtStamp = (ts) => (typeof ts === 'string' && ts.length >= 16
  ? ts.slice(0, 16).replace('T', ' ') + ' UTC' : NA);
const fmtClock = (d) => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

/* ── Session (unchanged mechanism: localStorage id sent as session_id) ── */

const SID_KEY = 'galene_sid';
let sid = '';
try {
  sid = localStorage.getItem(SID_KEY) || '';
  if (!sid) {
    sid = (window.crypto && crypto.randomUUID)
      ? crypto.randomUUID()
      : 's-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
    localStorage.setItem(SID_KEY, sid);
  }
} catch (_) {
  sid = 's-' + Date.now().toString(36);
}

/* ── Query point ────────────────────────────────────────────────────── */

let lat = 15.0, lon = 74.0;

/* ══════════════════════════════════════════════════════════════════════
   MAP — Leaflet setup and layers (every /geo/* call preserved as-is)
   ══════════════════════════════════════════════════════════════════════ */

const map = L.map('map', { zoomControl: true }).setView([lat, lon], 5);

L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Esri, Maxar, Earthstar Geographics',
}).addTo(map);
// City/boundary labels (Esri reference, transparent, keyless — verified live).
const labelsLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Esri',
}).addTo(map);
// Ports, buoys, lights (OpenSeaMap seamarks, keyless — verified live).
const portsLayer = L.tileLayer('https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenSeaMap contributors',
  maxZoom: 18,
}).addTo(map);
// Sea/ocean names + undersea features (Esri Ocean reference, transparent, keyless).
const seasLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Esri',
}).addTo(map);

const eezLayer = L.layerGroup().addTo(map);
const mpaLayer = L.layerGroup().addTo(map);
const pfzLayer = L.layerGroup().addTo(map);
const marker = L.marker([lat, lon], {
  icon: L.divIcon({
    className: 'pt-icon',
    html: '<span class="pt-dot"></span>',
    iconSize: [16, 16], iconAnchor: [8, 8]
  })
}).addTo(map);
marker.bindPopup(function () { return '<b>Query point</b><br>' + esc(fmtPoint(lat, lon)); });

function layerToggle(id, layer, load) {
  $(id).onchange = (e) => {
    if (e.target.checked) {
      map.addLayer(layer);
      if (load) load();
    } else {
      map.removeLayer(layer);
    }
  };
}

function mapNote(title, endpoint, err) {
  const n = el('div', 'map-note');
  n.appendChild(el('b', null, title));
  n.appendChild(el('span', null, endpoint + ' did not respond' +
    (err && err.message ? ' (' + err.message + ')' : '') + '.'));
  $('mapwrap').appendChild(n);
}

async function loadGeo(path, layer, style, onEach) {
  try {
    const r = await fetch(path);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const gj = await r.json();
    L.geoJSON(gj, { style, onEachFeature: onEach }).addTo(layer);
  } catch (e) {
    layer.clearLayers();
    mapNote('Boundary layer unavailable', path, e);
  }
}
loadGeo('/geo/eez', eezLayer, { color: '#38bdf8', weight: 1.5, fillOpacity: 0.08 });
loadGeo('/geo/mpas', mpaLayer, { color: '#fbbf24', weight: 1.5, fillOpacity: 0.25 },
  (f, l) => l.bindPopup('<b>' + esc(f.properties.name || 'Protected area') + '</b><br>' +
    esc(f.properties.desig || '')));
layerToggle('lyr-eez', eezLayer);
layerToggle('lyr-mpa', mpaLayer);

async function loadPfz() {
  try {
    const r = await fetch('/geo/pfz');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const b = await r.json();
    pfzLayer.clearLayers();
    (b.zones || []).forEach((z) => {
      L.marker([z.lat, z.lon], {
        icon: L.divIcon({ className: 'pfz-icon', html: '<span></span>', iconSize: [14, 14], iconAnchor: [7, 7] })
      }).bindPopup('<b>Potential fishing zone</b><br>Depth: ' + esc(z.depth_m == null ? NA : z.depth_m) +
        ' m<br>' + esc(z.direction || '') + '<br><span class="prov">' +
        esc((b.provenance || {}).source || NA) + ' · ' + esc((b.provenance || {}).mode || NA) +
        '</span>').addTo(pfzLayer);
    });
  } catch (e) {
    mapNote('Fishing-zone layer unavailable', '/geo/pfz', e);
  }
}
loadPfz();
layerToggle('lyr-pfz', pfzLayer, loadPfz);

// Satellite true-colour overlay for the current view (CDSE Sentinel-2, cached).
let satLayer = null;
async function loadSat() {
  const b = map.getBounds();
  const q = 'minlon=' + b.getWest().toFixed(2) + '&minlat=' + b.getSouth().toFixed(2) +
    '&maxlon=' + b.getEast().toFixed(2) + '&maxlat=' + b.getNorth().toFixed(2);
  if (satLayer) map.removeLayer(satLayer);
  satLayer = L.imageOverlay('/geo/sat?' + q,
    [[b.getSouth(), b.getWest()], [b.getNorth(), b.getEast()]], { opacity: 0.85 });
  if ($('lyr-sat').checked) satLayer.addTo(map);
}
$('lyr-sat').onchange = (e) => {
  if (e.target.checked) { loadSat(); if (satLayer) satLayer.addTo(map); }
  else if (satLayer) map.removeLayer(satLayer);
};
map.on('moveend', () => { if ($('lyr-sat').checked) loadSat(); });

// IMD CAP alert polygons (live RSS; red=Severe, orange=Moderate, yellow=other).
const alertsLayer = L.layerGroup().addTo(map);
async function loadAlerts() {
  try {
    const r = await fetch('/geo/cyclones');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const b = await r.json();
    alertsLayer.clearLayers();
    const color = (s) => ({ Severe: '#ef4444', Extreme: '#ef4444', Moderate: '#f59e0b' }[s] || '#facc15');
    L.geoJSON(b.geojson, {
      style: (f) => ({ color: color(f.properties.severity), weight: 1.5, fillOpacity: 0.2 }),
      onEachFeature: (f, l) => l.bindPopup(
        '<b>' + esc(f.properties.headline || f.properties.event) + '</b><br>' +
        esc(f.properties.area || '') + '<br>Severity: ' + esc(f.properties.severity || NA) +
        '<br>Expires: ' + esc(f.properties.expires || NA))
    }).addTo(alertsLayer);
  } catch (e) {
    alertsLayer.clearLayers(); // offline: layer stays empty
  }
}
loadAlerts();
layerToggle('lyr-alerts', alertsLayer);

// SST productivity grid (Open-Meteo multi-location; blue→red).
const sstLayer = L.layerGroup().addTo(map);
function sstColor(v) {
  if (v == null) return '#64748b';
  if (v < 27) return '#38bdf8';
  if (v < 28.5) return '#4ade80';
  if (v < 29.5) return '#facc15';
  return '#ef4444';
}
async function loadSST() {
  const b = map.getBounds();
  const q = 'minlon=' + b.getWest().toFixed(2) + '&minlat=' + b.getSouth().toFixed(2) +
    '&maxlon=' + b.getEast().toFixed(2) + '&maxlat=' + b.getNorth().toFixed(2) + '&n=5';
  try {
    const r = await fetch('/geo/sst-grid?' + q);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    sstLayer.clearLayers();
    const cells = d.data ? d.data.cells : d.cells;
    const dLat = (b.getNorth() - b.getSouth()) / 5 / 2;
    const dLon = (b.getEast() - b.getWest()) / 5 / 2;
    const prov = d.provenance || {};
    (cells || []).forEach((c) => {
      if (c.sst == null) return;
      L.rectangle([[c.lat - dLat, c.lon - dLon], [c.lat + dLat, c.lon + dLon]], {
        color: sstColor(c.sst), weight: 0.5, fillOpacity: 0.35,
      }).bindPopup('SST: ' + Number(c.sst).toFixed(1) + ' °C<br><span class="prov">' +
        esc(prov.source || NA) + ' · ' + esc(prov.mode || NA) + '</span>').addTo(sstLayer);
    });
  } catch (e) { /* offline: layer stays empty */ }
}
loadSST();
layerToggle('lyr-sst', sstLayer, loadSST);

// Chlorophyll-proxy overlay (Sentinel-3 OLCI red-green ratio, relative scale).
let chlLayer = null;
async function loadChl() {
  const b = map.getBounds();
  const q = 'minlon=' + b.getWest().toFixed(2) + '&minlat=' + b.getSouth().toFixed(2) +
    '&maxlon=' + b.getEast().toFixed(2) + '&maxlat=' + b.getNorth().toFixed(2);
  if (chlLayer) map.removeLayer(chlLayer);
  chlLayer = L.imageOverlay('/geo/chl?' + q,
    [[b.getSouth(), b.getWest()], [b.getNorth(), b.getEast()]], { opacity: 0.55 });
  if ($('lyr-chl').checked) chlLayer.addTo(map);
}
$('lyr-chl').onchange = (e) => {
  if (e.target.checked) { loadChl(); if (chlLayer) chlLayer.addTo(map); }
  else if (chlLayer) map.removeLayer(chlLayer);
};
map.on('moveend', () => {
  if ($('lyr-sst').checked) loadSST();
  if ($('lyr-chl').checked) loadChl();
});

layerToggle('lyr-labels', labelsLayer);
layerToggle('lyr-ports', portsLayer);
layerToggle('lyr-seas', seasLayer);

/* ══════════════════════════════════════════════════════════════════════
   48h TIDE / WAVE / WIND CHART  (canvas, no dependencies)
   ══════════════════════════════════════════════════════════════════════ */

let chartData = null;
const SERIES = [
  { key: 'sea_level_m', color: '#0a6c9e', label: 'Tide (m)', unit: 'm' },
  { key: 'wave_m', color: '#b97a0d', label: 'Wave (m)', unit: 'm' },
  { key: 'wind_kmh', color: '#0d8b9a', label: 'Wind (km/h ÷10)', unit: 'km/h', scale: 0.1 }
];

function drawChart(hover) {
  const s = chartData;
  if (hover === undefined) hover = -1;
  const c = $('chart');
  const ctx = c.getContext('2d');
  const W = Math.max(200, c.clientWidth || 600);
  const H = Math.max(80, c.clientHeight || 132);
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  c.width = Math.round(W * dpr);
  c.height = Math.round(H * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  if (!s) return;

  const vals = SERIES.map((o) => (s[o.key] || []).map((v) => (v == null ? null : v * (o.scale || 1))));
  const all = vals.flat().filter((v) => v != null);
  if (!all.length) {
    ctx.fillStyle = '#93aac0'; ctx.font = '12px sans-serif';
    ctx.fillText(NA, 12, H / 2);
    return;
  }
  const mn = Math.min.apply(null, all), mx = Math.max.apply(null, all);

  const L = 36, B = 26, T = 26, R = 8;
  const X = (i) => (i / Math.max(1, s.times.length - 1)) * (W - L - R) + L;
  const Y = (v) => H - B - ((v - mn) / Math.max(mx - mn, 1e-6)) * (H - B - T);

  ctx.font = '10px sans-serif';
  ctx.strokeStyle = '#b8cbd9'; ctx.lineWidth = 1; ctx.beginPath();
  ctx.moveTo(L, T - 8); ctx.lineTo(L, H - B); ctx.lineTo(W - R, H - B); ctx.stroke();
  ctx.fillStyle = '#6a869f';
  ctx.fillText(mx.toFixed(1), 2, T);
  ctx.fillText(mn.toFixed(1), 2, H - B);
  ctx.fillText('m (wind ÷10)', 2, H - 8);

  ctx.textAlign = 'center';
  s.times.forEach((t, i) => {
    const hh = +String(t).slice(11, 13);
    if (hh % 12 === 0) {
      ctx.fillStyle = '#6a869f';
      ctx.fillText(String(t).slice(8, 10) + ' ' + String(t).slice(11, 13) + 'h', X(i), H - 10);
      ctx.strokeStyle = '#e6eef4'; ctx.beginPath();
      ctx.moveTo(X(i), T - 8); ctx.lineTo(X(i), H - B); ctx.stroke();
    }
  });
  ctx.textAlign = 'left';

  // legend with swatches — stride adapts so it never overflows a narrow canvas
  ctx.font = '10px sans-serif';
  let x0 = L + 6;
  SERIES.forEach((o) => {
    const w = ctx.measureText(o.label).width;
    if (x0 + 23 + w > W - 4) return;
    ctx.strokeStyle = o.color; ctx.lineWidth = 2.5; ctx.beginPath();
    ctx.moveTo(x0, 12); ctx.lineTo(x0 + 18, 12); ctx.stroke();
    ctx.fillStyle = '#24486b'; ctx.fillText(o.label, x0 + 23, 15);
    x0 += 18 + w + 16;
  });

  vals.forEach((vv, k) => {
    ctx.strokeStyle = SERIES[k].color; ctx.lineWidth = 1.6; ctx.beginPath();
    let pen = false;
    vv.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      if (pen) ctx.lineTo(X(i), Y(v)); else ctx.moveTo(X(i), Y(v));
      pen = true;
    });
    ctx.stroke();
  });

  const tip = $('charttip');
  if (hover >= 0 && hover < s.times.length) {
    ctx.strokeStyle = '#93aac0'; ctx.setLineDash([3, 3]); ctx.beginPath();
    ctx.moveTo(X(hover), T - 8); ctx.lineTo(X(hover), H - B); ctx.stroke(); ctx.setLineDash([]);
    const rows = ['<b>' + esc(String(s.times[hover]).slice(5, 16).replace('T', ' ')) + '</b>'];
    SERIES.forEach((o, k) => {
      const raw = (s[o.key] || [])[hover];
      rows.push('<span style="color:' + o.color + '">&#9679;</span> ' +
        esc(o.label.split(' (')[0]) + ': ' +
        (raw == null ? esc(NA)
          : esc(Number(raw).toFixed(Math.abs(raw) < 10 ? 2 : 1) + ' ' + o.unit)));
      if (raw != null) {
        ctx.fillStyle = o.color; ctx.beginPath(); ctx.arc(X(hover), Y(vals[k][hover]), 3.5, 0, 7); ctx.fill();
        ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.arc(X(hover), Y(vals[k][hover]), 1.5, 0, 7); ctx.fill();
      }
    });
    tip.innerHTML = rows.join('<br>');
    tip.style.display = 'block';
    tip.style.left = Math.max(4, Math.min(X(hover) + 12, W - 180)) + 'px';
    tip.style.top = '30px';
  } else {
    tip.style.display = 'none';
  }
  s._geom = { L, W, n: s.times.length };
}

async function loadChart() {
  try {
    const r = await fetch('/geo/series?lat=' + lat + '&lon=' + lon);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    chartData = (d && Array.isArray(d.times) && d.times.length) ? d : null;
    $('chartcap').textContent = chartData
      ? '48h tide / wave / wind at ' + fmtPoint(lat, lon) + ' — hover for values'
      : '48h tide / wave / wind — ' + NA;
  } catch (e) {
    chartData = null;
    $('chartcap').textContent = '48h tide / wave / wind — ' + NA;
  }
  drawChart(-1);
}
$('chart').addEventListener('mousemove', (e) => {
  if (!chartData || !chartData._geom) return;
  const rect = e.target.getBoundingClientRect();
  const g = chartData._geom;
  const i = Math.round(((e.clientX - rect.left - g.L) / Math.max(1, g.W - g.L - 8)) * (g.n - 1));
  drawChart(Math.max(0, Math.min(g.n - 1, i)));
});
$('chart').addEventListener('mouseleave', () => drawChart(-1));

/* ── Query point selection ──────────────────────────────────────────── */

function setPoint(newLat, newLon, opts) {
  lat = Math.round(newLat * 100) / 100;
  lon = Math.round(newLon * 100) / 100;
  marker.setLatLng([lat, lon]);
  const text = fmtPoint(lat, lon);
  $('loc').textContent = 'lat ' + lat.toFixed(2) + ', lon ' + lon.toFixed(2) +
    (opts && opts.fromDevice ? ' (device location)' : ' (click map to move)');
  $('loc-inline').textContent = text + ((opts && opts.fromDevice) ? ' · device' : '');
  $('fact-point').textContent = text;
  loadChart();
}
map.on('click', (e) => setPoint(e.latlng.lat, e.latlng.lng));
$('locate-btn').onclick = () => map.setView([lat, lon], map.getZoom());
$('geo-btn').onclick = () => {
  if (!navigator.geolocation) {
    $('loc-inline').textContent = fmtPoint(lat, lon) + ' · geolocation unavailable';
    return;
  }
  $('geo-btn').disabled = true;
  navigator.geolocation.getCurrentPosition(
    (p) => { setPoint(p.coords.latitude, p.coords.longitude, { fromDevice: true }); $('geo-btn').disabled = false; },
    () => { $('loc-inline').textContent = fmtPoint(lat, lon) + ' · location permission denied'; $('geo-btn').disabled = false; },
    { timeout: 8000 }
  );
};

/* Layer + legend panels collapse on narrow screens so they never cover the map. */
if (window.matchMedia('(max-width: 860px)').matches) {
  $('layers-toggle').setAttribute('aria-expanded', 'false');
  $('legend').removeAttribute('open');
}
$('layers-toggle').onclick = () => {
  const t = $('layers-toggle');
  t.setAttribute('aria-expanded', t.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
};

/* The map container height depends on viewport height; keep tiles correct. */
let resizeTimer = null;
const onResize = () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { map.invalidateSize(); drawChart(-1); }, 150);
};
window.addEventListener('resize', onResize);
window.addEventListener('orientationchange', onResize);

/* ══════════════════════════════════════════════════════════════════════
   HEALTH — GET /health (real backend liveness, backend/app/main.py:44)
   ══════════════════════════════════════════════════════════════════════ */

function setHealth(state, label, provider) {
  const box = $('health');
  box.className = 'status status--' + state;
  box.querySelector('.status-label').textContent = label;
  box.title = provider ? 'LLM provider: ' + provider : 'Backend liveness probe';
}

async function pollHealth() {
  try {
    const r = await fetch('/health', { cache: 'no-store' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    if (d && d.status === 'ok') setHealth('online', 'Systems Online', d.llm_provider);
    else setHealth('degraded', 'Systems Degraded', d && d.llm_provider);
  } catch (e) {
    setHealth('offline', 'Backend Unreachable');
  }
}
pollHealth();
setInterval(pollHealth, 30000);

/* ══════════════════════════════════════════════════════════════════════
   READING THE /ask RESPONSE — display only, never computation
   ══════════════════════════════════════════════════════════════════════ */

function normVerdict(v) {
  const k = String(v == null ? '' : v).toLowerCase();
  return Object.prototype.hasOwnProperty.call(VERDICTS, k) ? k : 'unknown';
}

const stepLabel = (s) => (s && s.agent) ? (s.tool ? s.agent + ' / ' + s.tool : s.agent) : NA;
const findStep = (trace, pred) => trace.find((s) => {
  try { return pred(s); } catch (_) { return false; }
});

const statusOf = (phrase) => {
  const p = String(phrase).toLowerCase();
  if (p.indexOf('exceed') !== -1) return 'bad';
  if (p.indexOf('caution') !== -1) return 'warn';
  if (p.indexOf('within') !== -1) return 'ok';
  return 'none';
};

/* Evidence rows are lifted from what the backend actually said — its risk
   reason templates (risk.py) and, for advisory intents, the ocean figures it
   states verbatim in its own answer. Strict patterns: no match, no row. */
function buildEvidence(body) {
  const answer = typeof body.answer === 'string' ? body.answer : '';
  const trace = (Array.isArray(body.trace) ? body.trace : []).filter((s) => s && s.agent);
  const reasons = (Array.isArray(body.reasons) ? body.reasons : []).filter((r) => r != null && String(r).trim());
  const rows = [];
  const forecast = () => findStep(trace, (s) => s.agent === 'weather' && s.tool === 'get_forecast');
  const alerts = () => findStep(trace, (s) => s.agent === 'weather' && s.tool === 'get_alerts');
  const riskStep = () => findStep(trace, (s) => s.agent === 'risk');

  reasons.forEach((r) => {
    const text = String(r);
    let m;
    if ((m = RE_WIND.exec(text))) {
      const st = forecast();
      rows.push({ label: 'Max wind', value: m[1], unit: 'km/h', note: m[2],
        source: st ? stepLabel(st) : NA, ts: st ? st.timestamp : null, status: statusOf(m[2]) });
    } else if ((m = RE_WAVE.exec(text))) {
      const st = forecast();
      rows.push({ label: 'Max wave height', value: m[1], unit: 'm', note: m[2],
        source: st ? stepLabel(st) : NA, ts: st ? st.timestamp : null, status: statusOf(m[2]) });
    } else if ((m = RE_IMD.exec(text))) {
      const st = alerts();
      rows.push({ label: 'IMD warning', value: m[1], unit: '',
        note: 'Official IMD district warning, raised by the backend risk engine.',
        source: st ? stepLabel(st) : NA, ts: st ? st.timestamp : null, status: 'warn' });
    } else {
      const st = riskStep();
      rows.push({ label: 'Risk reason', value: text, unit: '', note: 'Verbatim backend reason.',
        source: st ? stepLabel(st) : NA, ts: st ? st.timestamp : null, status: 'none' });
    }
  });

  const have = new Set(rows.map((r) => r.label));
  const extras = [
    { label: 'Potential fishing zones', re: RE_PFZ_COUNT, unit: ' zones',
      step: (s) => s.agent === 'ocean' && s.tool === 'get_pfz',
      note: 'Zones published for the KERALA sector.' },
    { label: 'Sea surface temperature', re: RE_SST, unit: '°C',
      step: (s) => s.agent === 'ocean' && s.tool === 'get_sst',
      note: 'Reading at the query point.' },
    { label: 'Chlorophyll', re: RE_CHL, unit: 'mg/m³',
      step: (s) => s.agent === 'ocean' && s.tool === 'get_chlorophyll',
      note: 'Satellite chlorophyll proxy.' }
  ];
  extras.forEach((x) => {
    if (have.has(x.label)) return;
    const m = x.re.exec(answer);
    if (!m) return;
    const st = findStep(trace, x.step);
    rows.push({ label: x.label, value: m[1], unit: x.unit, note: x.note,
      source: st ? stepLabel(st) : NA, ts: st ? st.timestamp : null, status: 'none' });
  });

  return rows;
}

function targetWindow(body) {
  const answer = typeof body.answer === 'string' ? body.answer : '';
  const m = RE_WINDOW.exec(answer) || RE_SNAPSHOT.exec(answer);
  return m ? m[1] + '  ' + m[2] + '–' + m[3] : NA;
}

function pipelineRows(body) {
  const trace = (Array.isArray(body.trace) ? body.trace : []).filter((s) => s && s.agent);
  const cites = (Array.isArray(body.citations) ? body.citations : []).filter(Boolean);
  const rows = [];
  PIPELINE.forEach((stage) => {
    if (!stage.match) {                        // Evidence / RAG: real citations only
      if (!cites.length) return;
      rows.push({ stage, steps: [{ label: 'retrieved', tool: cites.join(', '), ts: null }] });
      return;
    }
    const steps = trace.filter(stage.match);
    if (!steps.length) return;                 // never invent a stage
    rows.push({ stage, steps: steps.map((s) => ({ agent: s.agent, tool: s.tool, ts: s.timestamp })) });
  });
  return rows;
}

/* ══════════════════════════════════════════════════════════════════════
   RENDERERS
   ══════════════════════════════════════════════════════════════════════ */

const FLAGS = {
  ok: ['Within limits', 'ev-flag--ok'],
  warn: ['Caution', 'ev-flag--warn'],
  bad: ['Beyond limit', 'ev-flag--bad'],
  none: ['Reported', 'ev-flag--none']
};

function renderDecision(body) {
  const key = normVerdict(body.verdict);
  const v = VERDICTS[key];
  const panel = $('decision-panel');
  panel.dataset.state = 'answered';
  panel.dataset.verdict = key;

  const box = $('decision-verdict');
  box.classList.add('is-live');
  box.querySelector('.verdict-word').textContent = v.label;
  box.querySelector('.verdict-sub').textContent =
    key === 'info' ? 'Advisory question — no safety verdict was requested'
      : key === 'unknown' ? 'The backend returned a verdict this interface does not recognise'
        : 'Deterministic verdict from the backend risk engine';

  const reasons = (Array.isArray(body.reasons) ? body.reasons : []).filter(Boolean);
  $('decision-when').textContent = reasons.length
    ? reasons.length + ' reason' + (reasons.length === 1 ? '' : 's') + ' reported'
    : 'No risk reasons for this intent';

  const list = $('decision-reasons');
  list.innerHTML = '';
  if (reasons.length) reasons.forEach((r) => list.appendChild(el('li', null, String(r))));
  else list.appendChild(el('li', 'is-empty', 'The backend returned no risk reasons for this question.'));

  const win = $('fact-window');
  win.textContent = targetWindow(body);
  win.classList.toggle('is-empty', win.textContent === NA);
  win.title = 'Quoted from the window the backend names in its own answer.';

  // The risk engine returns a verdict and reasons, never a number.
  const score = $('fact-score');
  score.textContent = NA;
  score.title = 'POST /ask returns no numeric risk score, so the browser never invents one.';

  $('fact-degraded').textContent = body.degraded ? 'Fallback data in use' : 'Live';
  $('fact-degraded').style.color = body.degraded ? 'var(--caution-fg)' : '';
}

function evidenceNode(row) {
  const n = el('div', 'ev');
  n.appendChild(el('div', 'ev-label', row.label));

  const main = el('div', 'ev-main');
  const missing = row.value == null || row.value === '';
  const v = el('div', 'ev-value' + (missing ? ' is-empty' : ''));
  v.appendChild(document.createTextNode(missing ? NA : String(row.value)));
  if (row.unit && !missing) v.appendChild(el('span', 'unit', row.unit));
  main.appendChild(v);
  if (row.note) main.appendChild(el('div', 'ev-note', row.note));
  n.appendChild(main);

  const meta = el('div', 'ev-meta');
  const s1 = el('span');
  s1.appendChild(el('b', null, 'source '));
  s1.appendChild(document.createTextNode(row.source || NA));
  meta.appendChild(s1);

  const s2 = el('span');
  s2.appendChild(el('b', null, 'retrieved '));
  s2.appendChild(document.createTextNode(row.ts ? fmtStamp(row.ts) : NA));
  meta.appendChild(s2);

  const s3 = el('span');
  s3.appendChild(el('b', null, 'confidence '));
  s3.appendChild(document.createTextNode(NA));
  s3.title = 'POST /ask returns no per-metric confidence value.';
  meta.appendChild(s3);

  const flag = FLAGS[row.status] || FLAGS.none;
  meta.appendChild(el('span', 'ev-flag ' + flag[1], flag[0]));
  n.appendChild(meta);
  return n;
}

function renderEvidence(body) {
  const rows = buildEvidence(body);
  const list = $('evidence-list');
  list.innerHTML = '';

  if (!rows.length) {
    list.appendChild(el('p', 'trace-empty',
      'The backend returned no per-metric evidence for this question. The figures it does report are in the answer above.'));
    $('evidence-note').textContent = 'No per-metric evidence returned for this query';
  } else {
    rows.forEach((r, i) => {
      const n = evidenceNode(r);
      n.style.animationDelay = Math.min(i * 45, 260) + 'ms';
      list.appendChild(n);
    });
    $('evidence-note').textContent = 'Quoted verbatim from the backend answer and its execution trace';
  }

  const cites = (Array.isArray(body.citations) ? body.citations : []).filter(Boolean);
  const src = $('sources-list');
  src.innerHTML = '';
  if (cites.length) cites.forEach((c) => src.appendChild(el('span', 'src', String(c))));
  else src.appendChild(el('span', 'src is-empty', 'No RAG sources returned for this question'));
}

function renderTrace(body) {
  const raw = (Array.isArray(body.trace) ? body.trace : []).filter((s) => s && s.agent);
  const cites = (Array.isArray(body.citations) ? body.citations : []).filter(Boolean);
  const pane = $('trace-body');
  const summary = $('trace-summary');
  pane.innerHTML = '';

  // No trace steps came back — say so. Never fill the pipeline with guesses.
  if (!raw.length) {
    summary.textContent = 'No steps returned';
    pane.appendChild(el('p', 'trace-empty',
      'The backend returned no execution trace for this response, so no agent pipeline is shown.'));
    if (cites.length) {
      const s = el('p', 'trace-empty');
      s.appendChild(document.createTextNode('Sources returned with this response: '));
      cites.forEach((c) => s.appendChild(el('span', 'src', String(c))));
      pane.appendChild(s);
    }
    return;
  }

  const rows = pipelineRows(body);

  summary.textContent = rows.map((r) => r.stage.short).join(' → ');

  const ol = el('ol', 'pipeline');
  rows.forEach((r, si) => {
    // Every stage the backend reported is complete; the final one is the
    // stage that is live right now. Nothing is marked done that was not
    // actually returned.
    const isLast = si === rows.length - 1;
    const li = el('li', 'stage-row ' + (isLast ? 'is-active' : 'is-done'));
    const node = el('span', 'stage-node' + (isLast ? '' : ' is-done'));
    node.textContent = String(si + 1);
    li.appendChild(node);

    const sb = el('div', 'stage-body');
    const name = el('div', 'stage-name');
    name.appendChild(document.createTextNode(r.stage.name));
    name.appendChild(el('span', 'stage-count',
      ' · ' + r.steps.length + ' step' + (r.steps.length === 1 ? '' : 's')));
    sb.appendChild(name);

    const ul = el('ul', 'stage-steps');
    r.steps.forEach((s, i) => {
      const step = el('li');
      step.style.animationDelay = Math.min(si * 40 + i * 30, 420) + 'ms';
      if (s.agent) step.appendChild(el('span', null, s.agent));
      if (s.tool) step.appendChild(el('span', 'tool', s.tool));
      step.appendChild(el('span', 'stamp', s.ts ? fmtStamp(s.ts) : ''));
      ul.appendChild(step);
    });
    sb.appendChild(ul);
    li.appendChild(sb);
    ol.appendChild(li);
  });
  pane.appendChild(ol);
}

$('trace-toggle').onclick = () => {
  const t = $('trace-toggle');
  const open = t.getAttribute('aria-expanded') === 'true';
  t.setAttribute('aria-expanded', String(!open));
  $('trace-body').hidden = open;
};

/* ── Answer formatting (existing highlight behaviour, kept) ─────────── */

function highlight(text) {
  let h = esc(text);
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  h = h.replace(/\b\d+(\.\d+)?\s?%/g, (m) => '<span class="hl pct">' + m + '</span>');
  h = h.replace(/\b\d+(\.\d+)?\s?(km\/h|m\b|°C|\bC\b|mg\/m³|km\b|NM\b)/g,
    (m) => '<span class="hl num">' + m + '</span>');
  h = h.replace(/\(?\b-?\d{1,2}\.\d+,\s?-?\d{1,3}\.\d+\)?/g, (m) => '<span class="hl coord">' + m + '</span>');
  h = h.replace(/\b(WARNING|AVOID|UNSAFE|outside.{0,20}EEZ|OUTSIDE.{0,20}EEZ)\b/gi,
    (m) => '<span class="hl danger">' + m + '</span>');
  return h;
}

/* ── Conversation history ───────────────────────────────────────────── */
/* The backend keeps its own turn memory against session_id but exposes no
   history endpoint, so the visible transcript is built from the responses this
   page actually received. */
const chat = $('chat');
const scrollChat = () => { chat.scrollTop = chat.scrollHeight; };

function addUserTurn(text) {
  const t = el('article', 'turn turn--user');
  t.appendChild(el('p', 'turn-q', text));
  chat.appendChild(t);
  const empty = chat.querySelector('.turn--empty');
  if (empty) empty.remove();
}

function section(title, node, emptyText) {
  const s = el('div', 'turn-sec');
  s.appendChild(el('h4', null, title));
  if (node) s.appendChild(node);
  else s.appendChild(el('p', 'is-empty', emptyText));
  return s;
}

function plainText(text) { return el('p', null, text); }

function addBotTurn(body) {
  const v = VERDICTS[normVerdict(body.verdict)];
  const t = el('article', 'turn turn--bot');

  const head = el('div', 'turn-head');
  head.appendChild(el('span', 'turn-who', 'Galene'));
  head.appendChild(el('span', 'verdict-chip ' + v.chip, v.label));
  if (body.degraded) head.appendChild(el('span', 'ev-flag ev-flag--warn', 'Fallback data'));
  head.appendChild(el('span', 'turn-time', fmtClock(new Date())));
  t.appendChild(head);

  const ans = el('div', 'turn-answer');
  ans.innerHTML = highlight(typeof body.answer === 'string' && body.answer ? body.answer : NA);
  t.appendChild(ans);

  const secs = el('div', 'turn-sections');

  const dec = el('div', 'turn-decision');
  dec.appendChild(el('span', 'verdict-chip ' + v.chip, v.label));
  dec.appendChild(el('span', 'turn-decision-note',
    body.degraded
      ? 'Returned with degraded = true (fallback data in use).'
      : 'Returned with degraded = false.'));
  dec.appendChild(el('span', 'turn-decision-note',
    'Risk score and numeric confidence are not returned by /ask, so they are not shown.'));
  secs.appendChild(section('Decision', dec, NA));

  const win = targetWindow(body);
  secs.appendChild(section('Target window',
    win === NA ? null : plainText(win), NA));

  const reasons = (Array.isArray(body.reasons) ? body.reasons : []).filter(Boolean);
  let rnode = null;
  if (reasons.length) {
    const ul = el('ul');
    reasons.forEach((r) => ul.appendChild(el('li', null, String(r))));
    rnode = ul;
  }
  secs.appendChild(section('Reasons', rnode, 'No risk reasons for this intent.'));

  const evRows = buildEvidence(body);
  let evNode = null;
  if (evRows.length) {
    evNode = el('div');
    evRows.forEach((r) => {
      const line = el('p');
      line.appendChild(el('b', null, r.label + ': '));
      line.appendChild(document.createTextNode(
        (r.value == null || r.value === '') ? NA : String(r.value) + (r.unit ? ' ' + r.unit : '')));
      evNode.appendChild(line);
    });
  }
  secs.appendChild(section('Evidence', evNode, 'No per-metric evidence returned.'));

  const cites = (Array.isArray(body.citations) ? body.citations : []).filter(Boolean);
  let citeNode = null;
  if (cites.length) {
    citeNode = el('div');
    cites.forEach((c) => citeNode.appendChild(el('span', 'src', String(c))));
  }
  secs.appendChild(section('Sources', citeNode, 'No RAG sources returned.'));

  const pipeline = pipelineRows(body);
  let traceNode = null;
  if (pipeline.length) {
    const ol = el('ol');
    pipeline.forEach((r) => {
      const li = el('li');
      li.appendChild(el('span', 'tool', r.stage.name));
      ol.appendChild(li);
    });
    traceNode = ol;
  }
  secs.appendChild(section('Trace', traceNode, 'No execution trace returned.'));

  t.appendChild(secs);
  chat.appendChild(t);
}

/* ── Notices ────────────────────────────────────────────────────────── */

function showDegraded(on, detail) {
  $('notice-degraded').hidden = !on;
  if (on && detail) $('notice-degraded-text').textContent = detail;
}

function showError(on, text) {
  $('notice-error').hidden = !on;
  if (on && text) $('notice-error-text').textContent = text;
}

/* ── Loading: "GALENE IS ANALYZING" ─────────────────────────────────── */

let stageTimers = [];
let stageRun = 0;

function buildStageList() {
  const ol = $('analyzing-stages');
  ol.innerHTML = '';
  ANALYZE_STAGES.forEach((name, i) => {
    const li = el('li', i === 0 ? 'is-active' : '', name);
    li.style.transitionDelay = (i * 30) + 'ms';
    ol.appendChild(li);
  });
}

function stopStages() {
  stageTimers.forEach(clearTimeout);
  stageTimers = [];
  stageRun++;
  $('analyzing').hidden = true;
}

function startStages() {
  stageTimers.forEach(clearTimeout);
  stageTimers = [];
  const run = ++stageRun;
  const items = Array.prototype.slice.call($('analyzing-stages').children);

  items.forEach((li, i) => { li.className = i === 0 ? 'is-active' : ''; });
  $('analyzing').querySelector('.analyzing-title').textContent =
    'Galene is exploring the ocean';
  $('analyzing').hidden = false;

  STAGE_TIMING.forEach((delay, i) => {
    stageTimers.push(setTimeout(() => {
      if (run !== stageRun) return;
      if (i < items.length) {
        items.forEach((li, k) => {
          li.className = k < i ? 'is-done' : (k === i ? 'is-active' : '');
        });
        items[i].className = 'is-active';
      }
      if (i === STAGE_TIMING.length - 1) {
        $('analyzing').querySelector('.analyzing-title').textContent =
          'Galene is still exploring the ocean';
      }
    }, delay));
  });
}

/* ── Demo / test states (?mock=…) — local copies only ───────────────── */

const MOCK = new URLSearchParams(location.search).get('mock');
const FIXTURES = window.GALENE_DEV_FIXTURES || null;
if (MOCK && FIXTURES && Object.prototype.hasOwnProperty.call(FIXTURES, MOCK)) {
  $('demo-banner').hidden = false;
}

/* ── Ask flow: POST /ask ────────────────────────────────────────────── */

let busy = false;
let lastQuestion = '';

async function ask(question) {
  if (busy) return;
  const q = String(question || '').trim();
  if (!q) return;

  busy = true;
  lastQuestion = q;
  addUserTurn(q);
  $('ask-input').value = '';
  $('ask-submit').disabled = true;
  $('ask-submit').classList.add('is-submitting');
  showError(false);

  buildStageList();
  startStages();

  const btn = $('ask-submit');
  const idleLabel = btn.textContent;

  let body = null;
  try {
    if (MOCK === 'error') throw new Error('Simulated transport failure');
    if (MOCK && FIXTURES && FIXTURES[MOCK]) {
      body = JSON.parse(JSON.stringify(FIXTURES[MOCK]));
    } else {
      const r = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, lat, lon, session_id: sid })
      });
      if (!r.ok) throw new Error('Backend returned HTTP ' + r.status);
      body = await r.json();
    }
  } catch (e) {
    stopStages();
    btn.textContent = idleLabel;
    btn.disabled = false;
    btn.classList.remove('is-submitting');
    busy = false;
    showError(true, 'Galene could not reach the backend ('
      + (e && e.message ? e.message : 'network error') + '). Nothing was fabricated — please retry.');
    const t = el('article', 'turn turn--bot');
    const head = el('div', 'turn-head');
    head.appendChild(el('span', 'turn-who', 'Galene'));
    head.appendChild(el('span', 'ev-flag ev-flag--bad', 'No response'));
    t.appendChild(head);
    t.appendChild(el('p', 'turn-answer is-empty',
      'The request failed before an answer was produced. No marine values are shown because none were received.'));
    chat.appendChild(t);
    scrollChat();
    return;
  }

  // The timed stages give way to the real trace the moment it arrives.
  stopStages();
  renderDecision(body);
  renderEvidence(body);
  renderTrace(body);
  addBotTurn(body);
  showDegraded(!!body.degraded, body.degraded
    ? 'Some live marine data is temporarily unavailable. Galene is using verified fallback data.'
    : '');
  btn.textContent = idleLabel;
  btn.disabled = false;
  btn.classList.remove('is-submitting');
  busy = false;
  scrollChat();
}

$('ask-form').onsubmit = (e) => { e.preventDefault(); ask($('ask-input').value); };

$('ask-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask($('ask-input').value); }
});

Array.prototype.forEach.call(document.querySelectorAll('.chip'), (chip) => {
  chip.addEventListener('click', () => ask(chip.dataset.q));
});

$('notice-retry').onclick = () => { if (lastQuestion) ask(lastQuestion); };

$('new-session').onclick = () => {
  try {
    sid = (window.crypto && crypto.randomUUID)
      ? crypto.randomUUID()
      : 's-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
    localStorage.setItem(SID_KEY, sid);
  } catch (_) { sid = 's-' + Date.now().toString(36); }
  $('session-label').textContent = sid.slice(0, 8);
  chat.innerHTML = '';
  chat.appendChild(el('p', 'turn turn--empty',
    'No questions in this session yet. Ask Galene above — follow-up questions keep their context.'));
  showError(false);
  showDegraded(false);
};

/* ── About dialog ───────────────────────────────────────────────────── */

const aboutDialog = $('about-dialog');
$('about-btn').onclick = () => {
  if (typeof aboutDialog.showModal === 'function') aboutDialog.showModal();
  else aboutDialog.setAttribute('open', '');
};

/* ── Ambient particle field (vanilla canvas, decorative only) ───────── */

(function oceanParticles() {
  const canvas = document.getElementById('ocean-particles');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const MAX = window.matchMedia('(min-width: 900px)').matches ? 46 : 22;
  let motes = [];
  let raf = 0;
  let running = false;
  let dpr = 1;

  function seed() {
    const w = canvas.clientWidth || window.innerWidth;
    const h = canvas.clientHeight || window.innerHeight;
    motes = [];
    const n = Math.min(MAX, Math.round((w * h) / 26000));
    for (let i = 0; i < n; i++) {
      motes.push({
        x: Math.random() * w,
        y: Math.random() * h,
        r: 0.6 + Math.random() * 1.7,
        vy: -(0.05 + Math.random() * 0.22),
        vx: (Math.random() - 0.5) * 0.07,
        a: 0.10 + Math.random() * 0.34,
        drift: Math.random() * Math.PI * 2
      });
    }
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(canvas.clientWidth * dpr);
    canvas.height = Math.round(canvas.clientHeight * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    seed();
  }

  function frame(t) {
    if (!running) return;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    for (let i = 0; i < motes.length; i++) {
      const p = motes[i];
      p.y += p.vy;
      p.drift += 0.008;
      p.x += p.vx + Math.sin(p.drift) * 0.14;
      if (p.y < -6) { p.y = h + 6; p.x = Math.random() * w; }
      if (p.x < -6) p.x = w + 6;
      if (p.x > w + 6) p.x = -6;
      // Very low alpha: atmosphere only, never a focal point.
      const pulse = 0.75 + 0.25 * Math.sin(t / 2200 + p.drift);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(98,230,242,' + (p.a * pulse).toFixed(3) + ')';
      ctx.fill();
    }
    raf = requestAnimationFrame(frame);
  }

  function start() {
    if (running || reduced.matches) return;
    running = true;
    raf = requestAnimationFrame(frame);
  }

  function stop() {
    running = false;
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
  }

  function sync() {
    // Reduced motion: draw one static frame, then never animate.
    if (reduced.matches) {
      stop();
      const w = canvas.clientWidth, h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);
      motes.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(98,230,242,' + (p.a * 0.7).toFixed(3) + ')';
        ctx.fill();
      });
      return;
    }
    start();
  }

  resize();
  sync();

  let rt = null;
  window.addEventListener('resize', () => {
    clearTimeout(rt);
    rt = setTimeout(resize, 180);
  });
  // Paused whenever the tab is hidden or the canvas is scrolled out of view.
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop(); else sync();
  });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (!e.isIntersecting) stop(); else sync(); });
    }, { threshold: 0 }).observe(canvas);
  }
  if (typeof reduced.addEventListener === 'function') {
    reduced.addEventListener('change', sync);
  }
})();

/* ── Boot ───────────────────────────────────────────────────────────── */

$('session-label').textContent = String(sid).slice(0, 8);
chat.appendChild(el('p', 'turn turn--empty',
  'No questions in this session yet. Ask Galene above — follow-up questions keep their context.'));
setPoint(lat, lon);
