"""Geo tools: check_geofence, plan_route. Deterministic geometry, no new deps.

Polygons are real but SIMPLIFIED (EEZ: MarineRegions MRGID 8480, tolerance
0.02deg; MPAs: 6 WDPA India marine sites) — demo use, NOT for navigation.
Ray-cast point-in-polygon + haversine + bbox segment check for the MPA detour.
"""

import math

from backend.app.data import static_geo
from backend.app.tools.schemas import GeofenceOut, LatLon, RouteOut


def _in_ring(lat: float, lon: float, ring: list) -> bool:
    inside, n = False, len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-12) + x1:
            inside = not inside
    return inside


def _in_geom(lat: float, lon: float, geom: dict) -> bool:
    if geom["type"] == "Polygon":
        return any(_in_ring(lat, lon, r) for r in geom["coordinates"])
    if geom["type"] == "MultiPolygon":
        return any(_in_ring(lat, lon, r) for poly in geom["coordinates"] for r in poly)
    return False


def _geom_bbox(geom: dict) -> tuple[list, list]:
    if geom["type"] == "Polygon":
        pts = [p for r in geom["coordinates"] for p in r]
    else:
        pts = [p for poly in geom["coordinates"] for r in poly for p in r]
    return [p[0] for p in pts], [p[1] for p in pts]


def check_geofence(point: LatLon) -> GeofenceOut:
    eez = static_geo.fetch_eez()["data"]
    mpas = static_geo.fetch_mpas()["data"]
    inside_eez = any(_in_geom(point.lat, point.lon, f["geometry"]) for f in eez["features"])
    inside_mpa, name = False, None
    for f in mpas["features"]:
        if _in_geom(point.lat, point.lon, f["geometry"]):
            inside_mpa, name = True, f["properties"].get("name")
            break
    return GeofenceOut(
        lat=point.lat,
        lon=point.lon,
        inside_eez=inside_eez,
        inside_mpa=inside_mpa,
        mpa_name=name,
        provenance=static_geo.fetch_eez()["provenance"],
    )


def _hav(a: LatLon, b: LatLon) -> float:
    r = 6371.0
    dLa, dLo = math.radians(b.lat - a.lat), math.radians(b.lon - a.lon)
    h = math.sin(dLa / 2) ** 2 + math.cos(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * math.sin(dLo / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _seg_hits_bbox(a: LatLon, b: LatLon, xs: list, ys: list) -> bool:
    # Sample-based bbox intersection (baseline only, documented).
    for t in [i / 20 for i in range(21)]:
        if min(xs) <= a.lon + (b.lon - a.lon) * t <= max(xs) and min(ys) <= a.lat + (b.lat - a.lat) * t <= max(ys):
            return True
    return False


def plan_route(start: LatLon, end: LatLon) -> RouteOut:
    mpas = static_geo.fetch_mpas()["data"]["features"]
    detoured, waypoints = False, [start, end]
    for f in mpas:
        xs, ys = _geom_bbox(f["geometry"])
        if _seg_hits_bbox(start, end, xs, ys):
            mid = LatLon(lat=(min(ys) + max(ys)) / 2 + 0.6, lon=(min(xs) + max(xs)) / 2)
            waypoints = [start, mid, end]
            detoured = True
            break
    dist = sum(_hav(waypoints[i], waypoints[i + 1]) for i in range(len(waypoints) - 1))
    return RouteOut(
        start=start, end=end, waypoints=waypoints, distance_km=round(dist, 2),
        detoured=detoured, provenance=static_geo.fetch_mpas()["provenance"],
    )
