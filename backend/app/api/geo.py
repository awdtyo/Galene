"""Read-only geo/frontend-data endpoints (fixtures, live series, satellite)."""

from fastapi import APIRouter, HTTPException, Response

from backend.app.data import openmeteo, satellite
from backend.app.data.static_geo import fetch_eez, fetch_mpas
from backend.app.tools import get_pfz

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/eez")
def eez():
    return fetch_eez()["data"]


@router.get("/mpas")
def mpas():
    return fetch_mpas()["data"]


@router.get("/pfz")
def pfz(sector: str = "KERALA"):
    return get_pfz(sector).model_dump()


@router.get("/series")
def series(lat: float, lon: float):
    """48h tide (sea level) + wave + wind series for charts. Open-Meteo live, fixture fallback."""
    m = openmeteo.fetch_marine(lat, lon)["data"].get("hourly", {})
    f = openmeteo.fetch_forecast(lat, lon)["data"].get("hourly", {})
    n = min(len(m.get("time", [])), len(f.get("time", [])), 48)
    return {
        "times": m.get("time", [])[:n],
        "sea_level_m": (m.get("sea_level_height_msl") or [None] * n)[:n],
        "wave_m": (m.get("wave_height") or [None] * n)[:n],
        "wind_kmh": (f.get("wind_speed_10m") or [None] * n)[:n],
    }


@router.get("/sat")
def sat(minlon: float, minlat: float, maxlon: float, maxlat: float):
    """Sentinel-2 true-colour PNG for the given bbox (CDSE, cached)."""
    try:
        tile = satellite.fetch_tile(minlon, minlat, maxlon, maxlat)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Satellite unavailable: {type(e).__name__}")
    return Response(content=tile["png"], media_type="image/png")
