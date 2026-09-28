"""Copernicus Marine (SST/chlorophyll) fetcher. STATUS: fixture-only.

Verified 2026-09-28:
- Data Store exists: https://data.marine.copernicus.eu/ (HTTP 200), products e.g.
  Global Ocean Colour / chlorophyll. Bulk download requires a (free) account +
  credentials/toolbox; not wired in Phase 1.
TODO: account + product IDs + credential handling. Until then: cache ->
fixture fallback. For live SST today use Open-Meteo marine SST (see openmeteo.py).
"""

from backend.app.data.cache import provenance, read_cache, read_fixture


def fetch_ocean_colour(lat: float, lon: float, *, use_cache: bool = True) -> dict:
    key = f"copernicus_colour_{lat:.2f}_{lon:.2f}"
    if use_cache:
        hit = read_cache(key)
        if hit is not None:
            return {"data": hit, "provenance": provenance("copernicus-marine/colour", "cache")}
    # TODO: authenticated product fetch
    return {"data": read_fixture("copernicus_colour"), "provenance": provenance("copernicus-marine/colour", "fixture")}
