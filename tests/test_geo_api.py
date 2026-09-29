from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_geo_eez():
    r = client.get("/geo/eez")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 1


def test_geo_mpas():
    r = client.get("/geo/mpas")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 6


def test_geo_pfz():
    r = client.get("/geo/pfz")
    assert r.status_code == 200
    body = r.json()
    assert body["sector"] == "KERALA" and len(body["zones"]) == 1
    assert "provenance" in body


def test_geo_series():
    r = client.get("/geo/series", params={"lat": 15.0, "lon": 74.0})
    assert r.status_code == 200
    body = r.json()
    assert len(body["times"]) == len(body["wave_m"]) == len(body["wind_kmh"]) > 0


def test_geo_sat_mocked(monkeypatch):
    from backend.app.api import geo as geo_mod

    monkeypatch.setattr(geo_mod.satellite, "fetch_tile", lambda *a, **k: {"png": b"PNG", "bounds": [], "cached": False})
    r = client.get("/geo/sat", params={"minlon": 73.9, "minlat": 14.9, "maxlon": 74.1, "maxlat": 15.1})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
