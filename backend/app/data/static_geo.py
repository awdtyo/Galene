"""Static-geo data: bathymetry (GEBCO), EEZ (MarineRegions), MPAs (WDPA). Fixture-only in Phase 1.

Verified 2026-09-28:
- GEBCO 2026 grid exists (https://download.gebco.net/, https://www.gebco.net/);
  global grid is GBs of netCDF/GeoTIFF — NOT fetched at runtime. Fixture holds
  a single illustrative depth value. Terms of use apply (see docs/data_sources.md).
- MarineRegions EEZ v12 exists (https://marineregions.org/downloads.php, CC-BY);
  full shapefile is ~122MB — NOT shipped. Fixture holds a simplified bbox
  polygon for India to enable offline geofence demos.
- Protected Planet WDPA API v4 exists (https://api.protectedplanet.net/) but
  needs a token; fixture holds 1-2 illustrative MPA polygons.
Nothing here fabricates a schema; fixtures are labelled mock/illustrative.
"""

from backend.app.data.cache import provenance, read_fixture


def fetch_depth(lat: float, lon: float) -> dict:
    return {"data": read_fixture("gebco_depth"), "provenance": provenance("gebco/grid", "fixture")}


def fetch_eez() -> dict:
    return {"data": read_fixture("eez_india_simplified"), "provenance": provenance("marineregions/eez", "fixture")}


def fetch_mpas() -> dict:
    return {"data": read_fixture("mpa_sample"), "provenance": provenance("wdpa/mpa", "fixture")}


def fetch_tides(lat: float, lon: float) -> dict:
    """No open India tide JSON API verified (Survey of India = RAR/ZIP tables;
    INCOIS PAT page has no open JSON). Fixture + Open-Meteo sea level proxy."""
    return {"data": read_fixture("tides"), "provenance": provenance("tides/fixture", "fixture")}
