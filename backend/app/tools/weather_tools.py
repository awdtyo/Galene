"""Weather tools: get_forecast, get_tides, get_alerts. No verdicts (Phase 3 Risk owns those)."""

from backend.app.data import imd
from backend.app.data import openmeteo as om
from backend.app.data import static_geo
from backend.app.tools.schemas import AlertsOut, ForecastHour, ForecastOut, LatLon, TideOut


def get_forecast(point: LatLon, *, hours: int = 12) -> ForecastOut:
    f = om.fetch_forecast(point.lat, point.lon)
    m = om.fetch_marine(point.lat, point.lon)
    fh, mh = f["data"].get("hourly", {}), m["data"].get("hourly", {})
    n = min(hours, len(fh.get("time", [])))
    rows = [
        ForecastHour(
            time=fh["time"][i],
            temperature_c=(fh.get("temperature_2m") or [None])[i],
            wind_kmh=(fh.get("wind_speed_10m") or [None])[i],
            weather_code=(fh.get("weather_code") or [None])[i],
            wave_height_m=(mh.get("wave_height") or [None])[i] if mh.get("wave_height") else None,
        )
        for i in range(n)
    ]
    return ForecastOut(lat=point.lat, lon=point.lon, hours=rows, provenance=f["provenance"])


def get_tides(point: LatLon) -> TideOut:
    out = static_geo.fetch_tides(point.lat, point.lon)
    d = out["data"]
    return TideOut(
        lat=point.lat,
        lon=point.lon,
        high_tide=d.get("high_tide"),
        low_tide=d.get("low_tide"),
        height_m=d.get("height_m"),
        provenance=out["provenance"],
    )


def get_alerts(point: LatLon, district_id: int = 573) -> AlertsOut:
    w = imd.fetch_imd_warning(district_id)
    m = om.fetch_marine(point.lat, point.lon)
    mh = m["data"].get("hourly", {})
    f = om.fetch_forecast(point.lat, point.lon)
    fh = f["data"].get("hourly", {})
    return AlertsOut(
        district_id=district_id,
        warnings=w["data"].get("warnings", []),
        wind_kmh=(fh.get("wind_speed_10m") or [None])[0],
        wave_height_m=(mh.get("wave_height") or [None])[0],
        provenance=w["provenance"],
    )
