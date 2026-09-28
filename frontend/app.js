// Phase 0 placeholder. Real chat + layers land in Phase 5.
const map = L.map("map").setView([15.0, 74.0], 5);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);
