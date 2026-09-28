"""IMD CAP alerts fetcher (VERIFIED live 2026-09-28).

- RSS: https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml (HTTP 200)
- Items link CAP XML with event/severity/areaDesc/polygon(lat,lon pairs)/expires.
- Cyclone best-track lines/cones are NOT published in machine form (RSMC
  publishes PNG/PDF bulletins only) — this fetcher covers alert polygons,
  which include cyclone-driven rainfall/wind alerts. No fabricated tracks.
Fallback: cache -> data/fixtures/cap_alerts.json.
"""

import re

import httpx

from backend.app.data.cache import provenance, read_cache, read_fixture, write_cache

RSS_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"


def _tag(xml: str, name: str) -> str:
    m = re.search(rf"<(?:cap:)?{name}>(.*?)</(?:cap:)?{name}>", xml, re.S)
    return m.group(1).strip() if m else ""


def _parse_alert(xml: str) -> dict | None:
    poly = _tag(xml, "polygon")
    if not poly:
        return None
    ring = []
    for pair in poly.split():
        lat, lon = pair.split(",")
        ring.append([float(lon), float(lat)])  # GeoJSON x,y
    return {
        "event": _tag(xml, "event"),
        "severity": _tag(xml, "severity"),
        "headline": _tag(xml, "headline"),
        "area": _tag(xml, "areaDesc"),
        "expires": _tag(xml, "expires"),
        "polygon": ring,
    }


def fetch_alerts(*, use_cache: bool = True, limit: int = 10) -> dict:
    if use_cache:
        hit = read_cache("cap_alerts")
        if hit is not None:
            return {"data": hit, "provenance": provenance("imd/cap", "cache")}
    try:
        items = re.findall(r"<item>(.*?)</item>", httpx.get(RSS_URL, timeout=20).text, re.S)[:limit]
        alerts = []
        for it in items:
            link = re.search(r"<link>(.*?)</link>", it, re.S)
            if not link:
                continue
            xml = httpx.get(link.group(1).strip(), timeout=20).text
            a = _parse_alert(xml)
            if a:
                alerts.append(a)
        data = {"alerts": alerts}
        write_cache("cap_alerts", data)
        return {"data": data, "provenance": provenance("imd/cap", "live")}
    except Exception:
        return {"data": read_fixture("cap_alerts"), "provenance": provenance("imd/cap", "fixture")}


def as_geojson(alerts: list[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {k: a[k] for k in ("event", "severity", "headline", "area", "expires")},
                "geometry": {"type": "Polygon", "coordinates": [a["polygon"]]},
            }
            for a in alerts
        ],
    }
