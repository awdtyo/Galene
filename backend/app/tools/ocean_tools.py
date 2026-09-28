"""Ocean tools: get_pfz, get_sst, get_chlorophyll. Typed over Phase 1 fetchers."""

from backend.app.data import copernicus, incois
from backend.app.data import openmeteo as om
from backend.app.tools.schemas import ChlorophyllOut, LatLon, PFZOut, PFZZone, SSTOut


def get_pfz(sector: str = "KERALA") -> PFZOut:
    out = incois.fetch_pfz(sector)
    d = out["data"]
    return PFZOut(
        sector=d.get("sector", sector),
        forecast_date=d.get("forecast_date"),
        valid_upto=d.get("valid_upto"),
        zones=[PFZZone(**z) for z in d.get("zones", [])],
        provenance=out["provenance"],
    )


def get_sst(point: LatLon) -> SSTOut:
    out = om.fetch_marine(point.lat, point.lon)
    d, hourly = out["data"], out["data"].get("hourly", {})
    sst = hourly.get("sea_surface_temperature", [None])[0]
    if sst is None:  # offline shape fallback via Copernicus fixture
        c = copernicus.fetch_ocean_colour(point.lat, point.lon)["data"]
        sst = float(c["sst_c"])
    t = (hourly.get("time") or [None])[0]
    return SSTOut(lat=point.lat, lon=point.lon, sst_c=float(sst), time=t, provenance=out["provenance"])


def get_chlorophyll(point: LatLon) -> ChlorophyllOut:
    out = copernicus.fetch_ocean_colour(point.lat, point.lon)
    d = out["data"]
    return ChlorophyllOut(
        lat=point.lat, lon=point.lon, chlorophyll_mg_m3=float(d["chlorophyll_mg_m3"]), provenance=out["provenance"]
    )
