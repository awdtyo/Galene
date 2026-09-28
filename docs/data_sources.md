# ORCA Data Sources — Phase 1 audit (verified 2026-09-28)

All endpoints below were probed live (HTTP status recorded). No fabricated URLs.
Anything not verified is marked TODO and ships fixture-only.

## Usable now (live, no key)

| Source | Verified endpoint | Access / format / update | Licence | ORCA use |
|---|---|---|---|---|
| Open-Meteo weather | `https://api.open-meteo.com/v1/forecast` (200, JSON) | No key, JSON hourly, ~7-8 day forecast, models update ~hourly/6-hourly | Free non-commercial, attribution to DWD/Open-Meteo required | `openmeteo.fetch_forecast` — wind/temp for safety query |
| Open-Meteo marine | `https://marine-api.open-meteo.com/v1/marine` (200, JSON; hourly `wave_height`, `sea_surface_temperature` verified) | No key, JSON hourly 7 days, wave/SST/sea-level-tide proxy | Same as above | `openmeteo.fetch_marine` — waves, SST, tide proxy |

Docs: https://open-meteo.com/en/docs (weather + marine).

## Fixture-only (needs key / account / structured access)

| Source | What was verified | Blocker | ORCA fallback |
|---|---|---|---|
| IMD warnings | API ref `https://api.imd.gov.in/public/api_reference.html` (200); `.../api/v1/districtwarning?id=573` → **401 `{"error":"API key missing"}`** | API key + IP whitelisting | `imd.fetch_imd_warning` → fixture |
| INCOIS PFZ | Sector text `.../MarineFisheries/TextDataHome?mfid=1` + `.../PfzAdvisory` pages exist (HTML, daily per-sector, 586 landing centres) | No open JSON API found | `incois.fetch_pfz` → fixture |
| INCOIS Ocean State Forecast | `.../oceanservices/osfforecast.jsp`, `https://sarat.incois.gov.in/OSF/` exist | No open JSON API found | `incois.fetch_ocean_state` → fixture; live via Open-Meteo |
| Copernicus Marine | Data Store `https://data.marine.copernicus.eu/` (200); chlorophyll/SST products exist | Free account + credentials/toolbox wiring | `copernicus.fetch_ocean_colour` → fixture; live SST via Open-Meteo |
| GEBCO 2026 | `https://download.gebco.net/` (200); 15 arc-sec global grid, netCDF/GeoTIFF | GBs — never fetch at runtime | `static_geo.fetch_depth` → illustrative fixture |
| MarineRegions EEZ v12 | `https://marineregions.org/downloads.php` (200); World EEZ v12 ~122MB | Too large to ship; CC-BY licence | `static_geo.fetch_eez` → simplified bbox fixture (labelled NOT real) |
| WDPA/Protected Planet MPAs | API v4 `https://api.protectedplanet.net/` (docs verified); token required | Token required; commercial use restricted | `static_geo.fetch_mpas` → illustrative fixture |
| India tides | Survey of India tide tables = RAR/ZIP downloads, no JSON API; INCOIS PAT page has no open JSON | No open JSON API verified | `static_geo.fetch_tides` → fixture + Open-Meteo sea-level proxy |

## TODO (Phase 1+ / Phase 2)
- IMD API key acquisition → wire keyed fetch in `imd.py`.
- INCOIS structured feed/scrape approval → replace PFZ/OSF fixtures.
- Copernicus account + product IDs → authenticated SST/chlorophyll.
- Real EEZ/MPA polygons (clipped to India coast) → replace simplified fixtures before any real geofencing.
- Lightning source: NOT verified — no fetcher built; candidate IMD Damini app / Blitzortung to audit in Phase 2.
