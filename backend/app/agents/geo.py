"""Geospatial agent: geofence warnings + safe routing. Wraps geo tools."""

from backend.app.api.schemas import now_iso
from backend.app.tools import LatLon, check_geofence, plan_route


def assess(point: LatLon, dest: LatLon | None, trace: list) -> dict:
    fence = check_geofence(point)
    trace.append({"agent": "geo", "tool": "check_geofence", "timestamp": now_iso()})
    out: dict = {"inside_eez": fence.inside_eez, "inside_mpa": fence.inside_mpa, "mpa_name": fence.mpa_name}
    if dest is not None:
        route = plan_route(point, dest)
        trace.append({"agent": "geo", "tool": "plan_route", "timestamp": now_iso()})
        out["route"] = route.model_dump()
    return out
