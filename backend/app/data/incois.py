"""INCOIS PFZ + Ocean State Forecast fetchers. STATUS: fixture-only.

Verified 2026-09-28:
- PFZ advisory pages exist (sector text + WebGIS), e.g.
  https://www.incois.gov.in/MarineFisheries/PfzAdvisory (describes daily PFZ
  maps/text per sector, 586 landing centres) and
  https://www.incois.gov.in/MarineFisheries/TextDataHome?mfid=1&request_locale=en
  (sector selector). These are HTML pages, NOT an open JSON API.
- Ocean State Forecast pages exist (e.g. https://incois.gov.in/oceanservices/osfforecast.jsp,
  https://sarat.incois.gov.in/OSF/) but no open JSON API was found.
TODO: structured scrape or official feed approval. Until then: cache ->
fixture fallback. Nothing here fabricates an endpoint.
"""

from backend.app.data.cache import provenance, read_cache, read_fixture


def fetch_pfz(sector: str = "KERALA", *, use_cache: bool = True) -> dict:
    key = f"incois_pfz_{sector.lower()}"
    if use_cache:
        hit = read_cache(key)
        if hit is not None:
            return {"data": hit, "provenance": provenance("incois/pfz", "cache")}
    # TODO: structured PFZ source
    return {"data": read_fixture("incois_pfz"), "provenance": provenance("incois/pfz", "fixture")}


def fetch_ocean_state(lat: float, lon: float, *, use_cache: bool = True) -> dict:
    key = f"incois_osf_{lat:.2f}_{lon:.2f}"
    if use_cache:
        hit = read_cache(key)
        if hit is not None:
            return {"data": hit, "provenance": provenance("incois/osf", "cache")}
    # TODO: structured OSF source; use Open-Meteo marine until then (see openmeteo.py)
    return {"data": read_fixture("incois_osf"), "provenance": provenance("incois/osf", "fixture")}
