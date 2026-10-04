"""Typed I/O for Phase 2 tools. All outputs carry provenance."""

from pydantic import BaseModel, Field


class LatLon(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Provenance(BaseModel):
    source: str
    mode: str
    fetched_at: str


class PFZZone(BaseModel):
    lat: float
    lon: float
    depth_m: float | None = None
    direction: str | None = None


class PFZOut(BaseModel):
    sector: str
    forecast_date: str | None = None
    valid_upto: str | None = None
    zones: list[PFZZone] = []
    provenance: Provenance


class SSTOut(BaseModel):
    lat: float
    lon: float
    sst_c: float
    time: str | None = None
    provenance: Provenance


class ChlorophyllOut(BaseModel):
    lat: float
    lon: float
    chlorophyll_mg_m3: float
    provenance: Provenance


class ForecastHour(BaseModel):
    time: str
    temperature_c: float | None = None
    wind_kmh: float | None = None
    weather_code: int | None = None
    wave_height_m: float | None = None
    cloud_cover_pct: float | None = None
    visibility_m: float | None = None


class ForecastOut(BaseModel):
    lat: float
    lon: float
    hours: list[ForecastHour] = []
    provenance: Provenance


class TideOut(BaseModel):
    lat: float
    lon: float
    high_tide: str | None = None
    low_tide: str | None = None
    height_m: float | None = None
    provenance: Provenance


class AlertsOut(BaseModel):
    district_id: int | None = None
    warnings: list[dict] = []
    wind_kmh: float | None = None
    wave_height_m: float | None = None
    provenance: Provenance


class GeofenceOut(BaseModel):
    lat: float
    lon: float
    inside_eez: bool
    inside_mpa: bool
    mpa_name: str | None = None
    note: str = "Real but simplified polygons (MarineRegions EEZ + WDPA MPAs) — NOT for navigation."
    provenance: Provenance


class RouteOut(BaseModel):
    start: LatLon
    end: LatLon
    waypoints: list[LatLon] = []
    distance_km: float
    detoured: bool
    provenance: Provenance
