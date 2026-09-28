"""IMD warnings fetcher. STATUS: fixture-only (API key required).

Verified 2026-09-28:
- API reference exists: https://api.imd.gov.in/public/api_reference.html (HTTP 200)
- Data endpoint e.g. https://api.imd.gov.in/api/v1/districtwarning?id=573
  returns HTTP 401 {"error":"API key missing"} without a key.
TODO Phase 1+: obtain IMD API key / IP whitelisting (see docs/data_sources.md),
then wire keyed fetch here. Until then: cache -> fixture fallback so the
demo works offline. No URL is fabricated; only the verified endpoint above.
"""

from backend.app.data.cache import provenance, read_cache, read_fixture


def fetch_imd_warning(district_id: int = 573, *, use_cache: bool = True) -> dict:
    key = f"imd_warning_{district_id}"
    if use_cache:
        hit = read_cache(key)
        if hit is not None:
            return {"data": hit, "provenance": provenance("imd/districtwarning", "cache")}
    # TODO: keyed fetch to https://api.imd.gov.in/api/v1/districtwarning
    return {"data": read_fixture("imd_warning"), "provenance": provenance("imd/districtwarning", "fixture")}
