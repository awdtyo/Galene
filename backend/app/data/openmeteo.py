"""Open-Meteo forecast + marine fetchers. VERIFIED live (no key, JSON).

Endpoints (probed 2026-09-28, HTTP 200; cloud_cover+visibility re-verified
2026-10-04, HTTP 200, hourly keys include cloud_cover, visibility):
- https://api.open-meteo.com/v1/forecast
- https://marine-api.open-meteo.com/v1/marine
Docs: https://open-meteo.com/en/docs (marine + weather). Licence: free for
non-commercial use, attribution required (see docs/data_sources.md).
Fallback: file cache -> data/fixtures/openmeteo_*.json (offline demo).
Note: checked-in fixture predates cloud fields; code treats them as optional.
"""

import httpx

from backend.app.data.cache import provenance, read_cache, read_fixture, write_cache

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"


def fetch_forecast(lat: float, lon: float, *, use_cache: bool = True) -> dict:
    """Hourly weather forecast: wind, temperature, weather_code, cloud, visibility."""
    key = f"openmeteo_forecast_v2_{lat:.2f}_{lon:.2f}"  # v2: cloud_cover+visibility added 2026-10-04
    if use_cache:
        hit = read_cache(key)
        if hit is not None:
            return {"data": hit, "provenance": provenance("open-meteo/forecast", "cache")}
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,wind_speed_10m,weather_code,cloud_cover,visibility",
        "forecast_days": 2,
    }
    try:
        r = httpx.get(FORECAST_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        write_cache(key, data)
        return {"data": data, "provenance": provenance("open-meteo/forecast", "live")}
    except Exception:
        return {"data": read_fixture("openmeteo_forecast"), "provenance": provenance("open-meteo/forecast", "fixture")}


def fetch_marine(lat: float, lon: float, *, use_cache: bool = True) -> dict:
    """Hourly marine state: wave height, SST, sea level (tide proxy)."""
    key = f"openmeteo_marine_{lat:.2f}_{lon:.2f}"
    if use_cache:
        hit = read_cache(key)
        if hit is not None:
            return {"data": hit, "provenance": provenance("open-meteo/marine", "cache")}
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wave_height,sea_surface_temperature,sea_level_height_msl",
        "forecast_days": 2,
    }
    try:
        r = httpx.get(MARINE_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        write_cache(key, data)
        return {"data": data, "provenance": provenance("open-meteo/marine", "live")}
    except Exception:
        return {"data": read_fixture("openmeteo_marine"), "provenance": provenance("open-meteo/marine", "fixture")}


def fetch_sst_grid(minlon: float, minlat: float, maxlon: float, maxlat: float, n: int = 5) -> dict:
    """Current-hour SST over an n x n grid (single multi-location call)."""
    n = max(2, min(n, 7))
    lats = [minlat + (maxlat - minlat) * i / (n - 1) for i in range(n)]
    lons = [minlon + (maxlon - minlon) * j / (n - 1) for j in range(n)]
    pts = [(la, lo) for la in lats for lo in lons]
    try:
        r = httpx.get(
            MARINE_URL,
            params={
                "latitude": ",".join(f"{la:.2f}" for la, _ in pts),
                "longitude": ",".join(f"{lo:.2f}" for _, lo in pts),
                "hourly": "sea_surface_temperature",
                "forecast_days": 1,
                "current": "sea_surface_temperature",
            },
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        cells = []
        for (la, lo), item in zip(pts, body if isinstance(body, list) else []):
            cur = (item.get("current") or {}).get("sea_surface_temperature")
            cells.append({"lat": round(la, 2), "lon": round(lo, 2), "sst": cur})
        return {"data": {"cells": cells}, "provenance": provenance("open-meteo/marine-grid", "live")}
    except Exception:
        fx = read_fixture("openmeteo_marine")["hourly"]["sea_surface_temperature"][0]
        cells = [{"lat": round(la, 2), "lon": round(lo, 2), "sst": fx} for la, lo in pts]
        return {"data": {"cells": cells}, "provenance": provenance("open-meteo/marine-grid", "fixture")}
