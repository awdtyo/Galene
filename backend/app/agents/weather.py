"""Weather agent: marine-state summary for a time window. Wraps Phase 2 tools."""

from datetime import date, timedelta

from backend.app.api.schemas import now_iso
from backend.app.tools import LatLon, get_alerts, get_forecast, get_tides


def summarize(point: LatLon, trace: list, focus: str = "general") -> dict:
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
        "focus": focus,
        "max_wind_kmh": max(winds) if winds else None,
        "max_wave_m": max(waves) if waves else None,
        "warnings": al.warnings,
        "high_tide": td.high_tide,
        "low_tide": td.low_tide,
        "tide_height_m": td.height_m,
        "provenance": [fc.provenance, al.provenance],
    }


def summarize_sky(point: LatLon, trace: list) -> dict:
    """Night-sky summary for moon visibility. Tonight 18:00 -> tomorrow 04:00.

    Uses Open-Meteo cloud_cover (%) + visibility (m) + WMO weather_code.
    Returns None-safe averages; absent metrics stay None (never fabricated).
    """
    fc = get_forecast(point, hours=48)
    trace.append({"agent": "weather", "tool": "get_forecast", "timestamp": now_iso()})
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    def _hour(h) -> int:
        try:
            return int(h.time[11:13])
        except (IndexError, ValueError):
            return -1

    night = [
        h
        for h in fc.hours
        if (h.time.startswith(today) and _hour(h) >= 18)
        or (h.time.startswith(tomorrow) and _hour(h) <= 4)
    ]
    if not night:
        night = fc.hours[:12] if len(fc.hours) >= 12 else fc.hours
        window_label = "next 12h night proxy"
    else:
        window_label = f"{today} 18:00-{tomorrow} 04:00"
    clouds = [h.cloud_cover_pct for h in night if h.cloud_cover_pct is not None]
    vis = [h.visibility_m for h in night if h.visibility_m is not None]
    codes = [h.weather_code for h in night if h.weather_code is not None]
    return {
        "window": window_label,
        "focus": "sky",
        "avg_cloud_pct": round(sum(clouds) / len(clouds), 1) if clouds else None,
        "min_visibility_km": round(min(vis) / 1000.0, 1) if vis else None,
        "weather_codes": codes,
        "n_hours": len(night),
        "provenance": [fc.provenance],
    }
