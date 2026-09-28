"""Weather agent: marine-state summary for a time window. Wraps Phase 2 tools."""

from datetime import date, timedelta

from backend.app.api.schemas import now_iso
from backend.app.tools import LatLon, get_alerts, get_forecast, get_tides


def summarize(point: LatLon, trace: list) -> dict:
    fc = get_forecast(point, hours=48)
    trace.append({"agent": "weather", "tool": "get_forecast", "timestamp": now_iso()})
    al = get_alerts(point)
    trace.append({"agent": "weather", "tool": "get_alerts", "timestamp": now_iso()})
    td = get_tides(point)
    trace.append({"agent": "weather", "tool": "get_tides", "timestamp": now_iso()})

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    window = [h for h in fc.hours if h.time.startswith(tomorrow) and 4 <= int(h.time[11:13]) <= 11]
    if not window:  # baseline fallback: hours 24-36 of the 48h forecast
        window = fc.hours[24:36]
    winds = [h.wind_kmh for h in window if h.wind_kmh is not None]
    waves = [h.wave_height_m for h in window if h.wave_height_m is not None]
    return {
        "window": f"{tomorrow} 04:00-11:00",
        "max_wind_kmh": max(winds) if winds else None,
        "max_wave_m": max(waves) if waves else None,
        "warnings": al.warnings,
        "high_tide": td.high_tide,
        "provenance": [fc.provenance, al.provenance],
    }
