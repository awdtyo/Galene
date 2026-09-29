// Galene UI: chat -> POST /ask, EEZ/MPA/PFZ overlays, alert + trace viewer.
function newSid() {
  if (window.crypto && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return "sid-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
}
let sid = null;
try {
  sid = localStorage.getItem("galene_sid");
  if (!sid) { sid = newSid(); localStorage.setItem("galene_sid", sid); }
} catch { sid = newSid(); }

let lat = 15.0, lon = 74.0;

if (typeof L === "undefined") {
  document.getElementById("alert").textContent = "⚠️ Map library (Leaflet CDN) failed to load — chat still works.";
}
if (typeof L !== "undefined") {

const map = L.map("map", { zoomControl: true }).setView([lat, lon], 5);
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
  attribution: "Esri, Maxar, Earthstar Geographics",
}).addTo(map);
// City/boundary labels (Esri reference, transparent, keyless — verified live).
const labelsLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
  attribution: "Esri",
}).addTo(map);
// Ports, buoys, lights (OpenSeaMap seamarks, keyless — verified live).
const portsLayer = L.tileLayer("https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenSeaMap contributors",
  maxZoom: 18,
}).addTo(map);
// Sea/ocean names + undersea features (Esri Ocean reference, transparent, keyless — verified live).
const seasLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}", {
  attribution: "Esri",
}).addTo(map);

const eezLayer = L.layerGroup().addTo(map);
const mpaLayer = L.layerGroup().addTo(map);
let marker = L.marker([lat, lon]).addTo(map);
let pfzLayer = L.layerGroup().addTo(map);

async function loadGeo(path, layer, style) {
  const r = await fetch(path);
  const gj = await r.json();
  L.geoJSON(gj, { style }).addTo(layer);
}
loadGeo("/geo/eez", eezLayer, { color: "#38bdf8", weight: 1.5, fillOpacity: 0.08 });
loadGeo("/geo/mpas", mpaLayer, { color: "#fbbf24", weight: 1.5, fillOpacity: 0.25 });
async function loadPfz() {
  const r = await fetch("/geo/pfz");
  const b = await r.json();
  pfzLayer.clearLayers();
  (b.zones || []).forEach((z) => {
    L.marker([z.lat, z.lon]).bindPopup(`PFZ — depth ${z.depth_m ?? "?"} m<br>${z.direction ?? ""}`).addTo(pfzLayer);
  });
}
loadPfz();
document.getElementById("lyr-eez").onchange = (e) => e.target.checked ? map.addLayer(eezLayer) : map.removeLayer(eezLayer);
document.getElementById("lyr-mpa").onchange = (e) => e.target.checked ? map.addLayer(mpaLayer) : map.removeLayer(mpaLayer);
document.getElementById("lyr-pfz").onchange = (e) => e.target.checked ? map.addLayer(pfzLayer) : map.removeLayer(pfzLayer);

document.getElementById("lyr-labels").onchange = (e) => e.target.checked ? map.addLayer(labelsLayer) : map.removeLayer(labelsLayer);
document.getElementById("lyr-ports").onchange = (e) => e.target.checked ? map.addLayer(portsLayer) : map.removeLayer(portsLayer);
document.getElementById("lyr-seas").onchange = (e) => e.target.checked ? map.addLayer(seasLayer) : map.removeLayer(seasLayer);
// Satellite true-colour overlay for the current view (CDSE Sentinel-2, cached server-side).
let satLayer = null;
async function loadSat() {
  const b = map.getBounds();
  const q = `minlon=${b.getWest().toFixed(2)}&minlat=${b.getSouth().toFixed(2)}&maxlon=${b.getEast().toFixed(2)}&maxlat=${b.getNorth().toFixed(2)}`;
  const url = `/geo/sat?${q}`;
  if (satLayer) map.removeLayer(satLayer);
  satLayer = L.imageOverlay(url, [[b.getSouth(), b.getWest()], [b.getNorth(), b.getEast()]], { opacity: 0.85 });
  if (document.getElementById("lyr-sat").checked) satLayer.addTo(map);
}
document.getElementById("lyr-sat").onchange = (e) => {
  if (e.target.checked) { loadSat(); if (satLayer) satLayer.addTo(map); }
  else if (satLayer) map.removeLayer(satLayer);
};
map.on("moveend", () => { if (document.getElementById("lyr-sat").checked) loadSat(); });

// IMD CAP alert polygons (live RSS; red=Severe, orange=Moderate, yellow=other).
const alertsLayer = L.layerGroup().addTo(map);
async function loadAlerts() {
  try {
    const r = await fetch("/geo/cyclones");
    const b = await r.json();
    alertsLayer.clearLayers();
    const color = (s) => ({ Severe: "#ef4444", Extreme: "#ef4444", Moderate: "#f59e0b" }[s] || "#facc15");
    L.geoJSON(b.geojson, {
      style: (f) => ({ color: color(f.properties.severity), weight: 1.5, fillOpacity: 0.2 }),
      onEachFeature: (f, l) => l.bindPopup(`<b>${f.properties.headline || f.properties.event}</b><br>${f.properties.area || ""}<br>Severity: ${f.properties.severity || "?"}<br>Expires: ${f.properties.expires || "?"}`),
    }).addTo(alertsLayer);
  } catch { /* offline: layer stays empty */ }
}
loadAlerts();
document.getElementById("lyr-alerts").onchange = (e) => e.target.checked ? map.addLayer(alertsLayer) : map.removeLayer(alertsLayer);

// SST productivity grid (Open-Meteo multi-location; blue→red).
const sstLayer = L.layerGroup().addTo(map);
function sstColor(v) {
  if (v == null) return "#64748b";
  if (v < 27) return "#38bdf8";
  if (v < 28.5) return "#4ade80";
  if (v < 29.5) return "#facc15";
  return "#ef4444";
}
async function loadSST() {
  const b = map.getBounds();
  const q = `minlon=${b.getWest().toFixed(2)}&minlat=${b.getSouth().toFixed(2)}&maxlon=${b.getEast().toFixed(2)}&maxlat=${b.getNorth().toFixed(2)}&n=5`;
  try {
    const r = await fetch(`/geo/sst-grid?${q}`);
    const d = await r.json();
    sstLayer.clearLayers();
    const cells = d.data ? d.data.cells : d.cells;
    const dLat = (b.getNorth() - b.getSouth()) / 5 / 2, dLon = (b.getEast() - b.getWest()) / 5 / 2;
    (cells || []).forEach((c) => {
      if (c.sst == null) return;
      L.rectangle([[c.lat - dLat, c.lon - dLon], [c.lat + dLat, c.lon + dLon]], {
        color: sstColor(c.sst), weight: 0.5, fillOpacity: 0.35,
      }).bindPopup(`SST: ${c.sst.toFixed(1)} °C`).addTo(sstLayer);
    });
  } catch { /* offline */ }
}
loadSST();
document.getElementById("lyr-sst").onchange = (e) => e.target.checked ? map.addLayer(sstLayer) : map.removeLayer(sstLayer);

// Chlorophyll-proxy overlay (Sentinel-3 OLCI red-green ratio, relative scale).
let chlLayer = null;
async function loadChl() {
  const b = map.getBounds();
  const q = `minlon=${b.getWest().toFixed(2)}&minlat=${b.getSouth().toFixed(2)}&maxlon=${b.getEast().toFixed(2)}&maxlat=${b.getNorth().toFixed(2)}`;
  const url = `/geo/chl?${q}`;
  if (chlLayer) map.removeLayer(chlLayer);
  chlLayer = L.imageOverlay(url, [[b.getSouth(), b.getWest()], [b.getNorth(), b.getEast()]], { opacity: 0.55 });
  if (document.getElementById("lyr-chl").checked) chlLayer.addTo(map);
}
document.getElementById("lyr-chl").onchange = (e) => {
  if (e.target.checked) { loadChl(); if (chlLayer) chlLayer.addTo(map); }
  else if (chlLayer) map.removeLayer(chlLayer);
};
map.on("moveend", () => {
  if (document.getElementById("lyr-sst").checked) loadSST();
  if (document.getElementById("lyr-chl").checked) loadChl();
});

// 48h tide / wave / wind chart (canvas, no deps). Labels + hover details.
let chartData = null;
const SERIES = [
  { key: "sea_level_m", color: "#38bdf8", label: "Tide (m)" },
  { key: "wave_m", color: "#fbbf24", label: "Wave (m)" },
  { key: "wind_kmh", color: "#4ade80", label: "Wind (km/h ÷10)", scale: 0.1 },
];
function drawChart(hover = -1) {
  const s = chartData;
  if (!s) return;
  const c = document.getElementById("chart");
  const ctx = c.getContext("2d");
  const W = (c.width = c.clientWidth || 600), H = c.height;
  ctx.clearRect(0, 0, W, H);
  const vals = SERIES.map((o) => s[o.key].map((v) => (v == null ? null : v * (o.scale || 1))));
  const all = vals.flat().filter((v) => v != null);
  const mn = Math.min(...all), mx = Math.max(...all);
  const L = 34, B = 26;
  const X = (i) => (i / (s.times.length - 1)) * (W - L - 8) + L;
  const Y = (v) => H - B - ((v - mn) / Math.max(mx - mn, 1e-6)) * (H - B - 22);
  ctx.font = "10px sans-serif";
  // axes
  ctx.strokeStyle = "#94a3b8"; ctx.lineWidth = 1; ctx.beginPath();
  ctx.moveTo(L, 18); ctx.lineTo(L, H - B); ctx.lineTo(W - 8, H - B); ctx.stroke();
  ctx.fillStyle = "#94a3b8";
  ctx.fillText(mx.toFixed(1), 2, 24); ctx.fillText(mn.toFixed(1), 2, H - B);
  ctx.fillText("m (wind ÷10)", 2, H - 8);
  // x time labels every 12h: "28 00h"
  ctx.textAlign = "center";
  s.times.forEach((t, i) => {
    const hh = +t.slice(11, 13);
    if (hh % 12 === 0) {
      ctx.fillText(`${t.slice(8, 10)} ${t.slice(11, 13)}h`, X(i), H - 10);
      ctx.strokeStyle = "#1e3a5f"; ctx.beginPath(); ctx.moveTo(X(i), 18); ctx.lineTo(X(i), H - B); ctx.stroke();
    }
  });
  ctx.textAlign = "left";
  // legend with swatches
  SERIES.forEach((o, k) => {
    const x0 = L + 8 + k * 110;
    ctx.strokeStyle = o.color; ctx.lineWidth = 2.5; ctx.beginPath();
    ctx.moveTo(x0, 12); ctx.lineTo(x0 + 22, 12); ctx.stroke();
    ctx.fillStyle = "#e2e8f0"; ctx.fillText(o.label, x0 + 26, 15);
  });
  // series lines
  vals.forEach((vv, k) => {
    ctx.strokeStyle = SERIES[k].color; ctx.lineWidth = 1.5; ctx.beginPath();
    let pen = false;
    vv.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      pen ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v)); pen = true;
    });
    ctx.stroke();
  });
  // hover crosshair + dots
  const tip = document.getElementById("charttip");
  if (hover >= 0 && hover < s.times.length) {
    ctx.strokeStyle = "#64748b"; ctx.setLineDash([3, 3]); ctx.beginPath();
    ctx.moveTo(X(hover), 18); ctx.lineTo(X(hover), H - B); ctx.stroke(); ctx.setLineDash([]);
    const rows = [`<b>${s.times[hover].slice(5, 16).replace("T", " ")}</b>`];
    SERIES.forEach((o, k) => {
      const raw = s[o.key][hover];
      const unit = o.key === "wind_kmh" ? "km/h" : "m";
      rows.push(`<span style="color:${o.color}">●</span> ${o.label.split(" (")[0]}: ${raw == null ? "—" : raw.toFixed(raw < 10 ? 2 : 1) + " " + unit}`);
      if (raw != null) {
        ctx.fillStyle = o.color; ctx.beginPath(); ctx.arc(X(hover), Y(vals[k][hover]), 3.5, 0, 7); ctx.fill();
        ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(X(hover), Y(vals[k][hover]), 1.5, 0, 7); ctx.fill();
      }
    });
    tip.innerHTML = rows.join("<br>");
    tip.style.display = "block";
    tip.style.left = Math.min(X(hover) + 12, W - 170) + "px";
    tip.style.top = "24px";
  } else {
    tip.style.display = "none";
  }
  chartData._geom = { L, W, n: s.times.length };
}
async function loadChart() {
  const r = await fetch(`/geo/series?lat=${lat}&lon=${lon}`);
  chartData = await r.json();
  chartData._geom = null;
  drawChart();
}
document.getElementById("chart").addEventListener("mousemove", (e) => {
  if (!chartData || !chartData._geom) return;
  const rect = e.target.getBoundingClientRect();
  const { L, W, n } = chartData._geom;
  const i = Math.round(((e.clientX - rect.left - L) / (W - L - 8)) * (n - 1));
  drawChart(Math.max(0, Math.min(n - 1, i)));
});
document.getElementById("chart").addEventListener("mouseleave", () => drawChart(-1));
loadChart();

map.on("click", (e) => {
  lat = +e.latlng.lat.toFixed(2); lon = +e.latlng.lng.toFixed(2);
  marker.setLatLng([lat, lon]);
  document.getElementById("loc").textContent = `lat ${lat.toFixed(2)}, lon ${lon.toFixed(2)} (click map to move)`;
  loadChart();
});
} // end Leaflet guard — chat below works with or without the map

const chat = document.getElementById("chat");
// Escape HTML, then highlight key data: measures, percentages, coordinates, warnings.
function highlight(text) {
  let h = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  h = h.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  h = h.replace(/\b\d+(\.\d+)?\s?%/g, (m) => `<span class="hl pct">${m}</span>`);
  h = h.replace(/\b\d+(\.\d+)?\s?(km\/h|m\b|°C|\bC\b|mg\/m³|km\b|NM\b)/g, (m) => `<span class="hl num">${m}</span>`);
  h = h.replace(/\(?\b-?\d{1,2}\.\d+,\s?-?\d{1,3}\.\d+\)?/g, (m) => `<span class="hl coord">${m}</span>`);
  h = h.replace(/\b(WARNING|AVOID|UNSAFE|outside.{0,20}EEZ|OUTSIDE.{0,20}EEZ)\b/gi, (m) => `<span class="hl danger">${m}</span>`);
  return h;
}
function bubble(who, text) {
  const d = document.createElement("div");
  d.className = "msg " + who;
  if (who === "bot") d.innerHTML = highlight(text);
  else d.textContent = text;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
}

document.getElementById("form").onsubmit = async (e) => {
  e.preventDefault();
  const q = document.getElementById("q").value.trim();
  if (!q) return;
  document.getElementById("q").value = "";
  bubble("user", q);
  bubble("sys", "…");
  const r = await fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: q, lat, lon, session_id: sid }),
  });
  chat.lastChild.remove();
  const b = await r.json();
  bubble("bot", b.answer);
  const alert = document.getElementById("alert");
  const icon = { safe: "✅", caution: "⚠️", unsafe: "🚨", info: "ℹ️" }[b.verdict] || "ℹ️";
  alert.textContent = `${icon} ${b.verdict || "info"}${b.degraded ? " (degraded data)" : ""}`;
  alert.className = b.verdict || "info";
  const t = document.getElementById("trace");
  t.innerHTML = "";
  const add = (h, items) => {
    const p = document.createElement("p");
    p.innerHTML = `<b>${h}:</b> ${items}`;
    t.appendChild(p);
  };
  add("Reasons", (b.reasons || []).join("; ") || "—");
  add("Citations", (b.citations || []).join(", ") || "—");
  add("Trace", (b.trace || []).map((s) => `${s.agent}${s.tool ? "/" + s.tool : ""}@${s.timestamp}`).join("<br>"));
  document.getElementById("tracebox").open = true;
};
