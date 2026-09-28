"""Geospatial agent: geofence warnings + nearest-MPA distance + safe routing."""

import math

from backend.app.api.schemas import now_iso
from backend.app.data import static_geo
from backend.app.tools import LatLon, check_geofence, plan_route


def _nearest_mpa(point: LatLon) -> dict:
    best: dict = {"name": None, "distance_km": None}
    for f in static_geo.fetch_mpas()["data"]["features"]:
        g = f["geometry"]
        pts = [p for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]) for r in poly for p in r]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        d = math.dist((point.lon, point.lat), (cx, cy)) * 111.0
        if best["distance_km"] is None or d < best["distance_km"]:
            best = {"name": f["properties"].get("name"), "distance_km": round(d, 1)}
    return best


def assess(point: LatLon, dest: LatLon | None, trace: list) -> dict:
    fence = check_geofence(point)
    trace.append({"agent": "geo", "tool": "check_geofence", "timestamp": now_iso()})
    out: dict = {
        "inside_eez": fence.inside_eez,
        "inside_mpa": fence.inside_mpa,
        "mpa_name": fence.mpa_name,
        "nearest_mpa": _nearest_mpa(point),
    }
    if dest is not None:
        route = plan_route(point, dest)
        trace.append({"agent": "geo", "tool": "plan_route", "timestamp": now_iso()})
        out["route"] = route.model_dump()
    return out
