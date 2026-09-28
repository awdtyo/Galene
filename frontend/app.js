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

map.on("click", (e) => {
  lat = +e.latlng.lat.toFixed(2); lon = +e.latlng.lng.toFixed(2);
  marker.setLatLng([lat, lon]);
  document.getElementById("loc").textContent = `lat ${lat.toFixed(2)}, lon ${lon.toFixed(2)} (click map to move)`;
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
