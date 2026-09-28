"""Copernicus data: CDSE OAuth token (VERIFIED live) + ocean-colour fixture.

Verified 2026-09-28:
- These credentials are Copernicus Data Space Ecosystem (Sentinel Hub) OAuth
  client credentials, NOT Copernicus Marine toolbox username/password.
- Token endpoint (from official CDSE docs, probed live HTTP 200):
  POST https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token
  grant_type=client_credentials -> Bearer token, ~1800s expiry.
- The token authorises CDSE/Sentinel Hub APIs (imagery, catalog). Wiring a
  Sentinel product call is a later phase (product IDs unverified).
- Copernicus Marine Data Store (https://data.marine.copernicus.eu/) needs a
  separate toolbox username/password — NOT these credentials.
fetch_ocean_colour stays fixture-backed (cache -> fixture). For live SST
today use Open-Meteo marine SST (see openmeteo.py).
"""

import httpx

from backend.app.config import settings
from backend.app.data.cache import provenance, read_cache, read_fixture, write_cache

CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"


def get_cdse_token(*, use_cache: bool = True) -> dict:
    """Fetch (and cache) a CDSE Bearer token. Raises RuntimeError without creds."""
    cid, sec = settings.COPERNICUS_CLIENT_ID.strip(), settings.COPERNICUS_CLIENT_SECRET.strip()
    if not cid or not sec:
        raise RuntimeError("Copernicus credentials missing (ORCA_COPERNICUS_CLIENT_ID/_SECRET).")
    if use_cache:
        hit = read_cache("cdse_token", ttl_s=1500)
        if hit is not None:
            return {"data": hit, "provenance": provenance("cdse/oauth", "cache")}
    r = httpx.post(
        CDSE_TOKEN_URL,
        data={"grant_type": "client_credentials", "client_id": cid, "client_secret": sec},
        timeout=20,
    )
    r.raise_for_status()
    data = {"access_token": r.json()["access_token"], "token_type": "Bearer"}
    # File cache dir is gitignored; token TTL 1500s < server expiry 1800s.
    write_cache("cdse_token", data)
    return {"data": data, "provenance": provenance("cdse/oauth", "live")}


def fetch_ocean_colour(lat: float, lon: float, *, use_cache: bool = True) -> dict:
    key = f"copernicus_colour_{lat:.2f}_{lon:.2f}"
    if use_cache:
        hit = read_cache(key)
        if hit is not None:
            return {"data": hit, "provenance": provenance("copernicus-marine/colour", "cache")}
    # TODO: authenticated product fetch (CDSE token verified; product call TBD)
    return {"data": read_fixture("copernicus_colour"), "provenance": provenance("copernicus-marine/colour", "fixture")}
