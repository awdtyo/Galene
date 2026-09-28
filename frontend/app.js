// Galene UI: chat -> POST /ask, EEZ/MPA/PFZ overlays, alert + trace viewer.
let lat = 15.0, lon = 74.0;
let sid = localStorage.getItem("galene_sid") || (localStorage.setItem("galene_sid", crypto.randomUUID()), localStorage.getItem("galene_sid"));

const map = L.map("map").setView([lat, lon], 5);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
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
loadGeo("/geo/eez", eezLayer, { color: "#0369a1", weight: 1.5, fillOpacity: 0.05 });
loadGeo("/geo/mpas", mpaLayer, { color: "#b45309", weight: 1.5, fillOpacity: 0.25 });
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

// 48h tide / wave / wind chart (canvas, no deps).
async function loadChart() {
  const r = await fetch(`/geo/series?lat=${lat}&lon=${lon}`);
  const s = await r.json();
  const c = document.getElementById("chart");
  const ctx = c.getContext("2d");
  const W = (c.width = c.clientWidth || 600), H = c.height;
  ctx.clearRect(0, 0, W, H);
  const series = [
    { key: "sea_level_m", color: "#0369a1", label: "tide m" },
    { key: "wave_m", color: "#b45309", label: "wave m" },
    { key: "wind_kmh", color: "#15803d", label: "wind/10" },
  ];
  const vals = series.map((o) => s[o.key].map((v, i) => (v == null ? null : o.key === "wind_kmh" ? v / 10 : v)));
  const all = vals.flat().filter((v) => v != null);
  const mn = Math.min(...all), mx = Math.max(...all);
  const X = (i) => (i / (s.times.length - 1)) * (W - 40) + 30;
  const Y = (v) => H - 15 - ((v - mn) / Math.max(mx - mn, 1e-6)) * (H - 30);
  ctx.strokeStyle = "#ccc"; ctx.beginPath(); ctx.moveTo(30, 5); ctx.lineTo(30, H - 15); ctx.lineTo(W - 5, H - 15); ctx.stroke();
  ctx.fillStyle = "#333"; ctx.font = "10px sans-serif";
  ctx.fillText(mx.toFixed(1), 2, 12); ctx.fillText(mn.toFixed(1), 2, H - 16);
  vals.forEach((vv, k) => {
    ctx.strokeStyle = series[k].color; ctx.lineWidth = 1.5; ctx.beginPath();
    let pen = false;
    vv.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      pen ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v)); pen = true;
    });
    ctx.stroke();
  });
  ctx.fillText(series.map((o) => o.label).join("  "), 34, 12);
}
loadChart();

map.on("click", (e) => {
  lat = +e.latlng.lat.toFixed(2); lon = +e.latlng.lng.toFixed(2);
  marker.setLatLng([lat, lon]);
  document.getElementById("loc").textContent = `lat ${lat.toFixed(2)}, lon ${lon.toFixed(2)} (click map to move)`;
  loadChart();
});

const chat = document.getElementById("chat");
function bubble(who, text) {
  const d = document.createElement("div");
  d.className = "msg " + who;
  d.textContent = text;
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
  alert.textContent = `Verdict: ${b.verdict || "info"}${b.degraded ? " (degraded data)" : ""}`;
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
