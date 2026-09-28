"""Static-geo data: bathymetry (GEBCO), EEZ (MarineRegions), MPAs (WDPA).

- GEBCO 2026 grid (https://download.gebco.net/) is GBs — NOT fetched at
  runtime. Fixture holds a single illustrative depth value.
- EEZ: real Indian EEZ polygon from MarineRegions WFS
  (https://geo.vliz.be/geoserver/MarineRegions/wfs, MRGID 8480, v12,
  CC-BY), simplified (Douglas-Peucker 0.02deg) to ~75KB in
  data/fixtures/eez_india.geojson. Demo use, NOT for navigation.
- MPAs: real India marine PAs from WDPA public ArcGIS REST
  (https://data-gis.unep-wcmc.org/server/rest/services/ProtectedPlanet/WDPCA/FeatureServer,
  filter prnt_iso3='IND' AND gis_m_area>0, 6 features) in
  data/fixtures/mpa_india.geojson. Demo use, NOT for navigation.
Nothing here fabricates a schema; pull details in docs/data_sources.md.
"""

from backend.app.data.cache import provenance, read_fixture


def fetch_depth(lat: float, lon: float) -> dict:
    return {"data": read_fixture("gebco_depth"), "provenance": provenance("gebco/grid", "fixture")}


def fetch_eez() -> dict:
    return {"data": read_fixture("eez_india"), "provenance": provenance("marineregions/eez", "fixture")}


def fetch_mpas() -> dict:
    return {"data": read_fixture("mpa_india"), "provenance": provenance("wdpa/mpa", "fixture")}


def fetch_tides(lat: float, lon: float) -> dict:
    """No open India tide JSON API verified (Survey of India = RAR/ZIP tables;
    INCOIS PAT page has no open JSON). Fixture + Open-Meteo sea level proxy."""
    return {"data": read_fixture("tides"), "provenance": provenance("tides/fixture", "fixture")}
