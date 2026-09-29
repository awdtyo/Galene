"""Open-Meteo forecast + marine fetchers. VERIFIED live (no key, JSON).

Endpoints (probed 2026-09-28, HTTP 200):
- https://api.open-meteo.com/v1/forecast
- https://marine-api.open-meteo.com/v1/marine
Docs: https://open-meteo.com/en/docs (marine + weather). Licence: free for
non-commercial use, attribution required (see docs/data_sources.md).
Fallback: file cache -> data/fixtures/openmeteo_*.json (offline demo).
"""

import httpx

from backend.app.data.cache import provenance, read_cache, read_fixture, write_cache

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"


def fetch_forecast(lat: float, lon: float, *, use_cache: bool = True) -> dict:
    """Hourly weather forecast: wind, temperature, weather_code."""
    key = f"openmeteo_forecast_{lat:.2f}_{lon:.2f}"
    if use_cache:
        hit = read_cache(key)
        if hit is not None:
            return {"data": hit, "provenance": provenance("open-meteo/forecast", "cache")}
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,wind_speed_10m,weather_code",
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
