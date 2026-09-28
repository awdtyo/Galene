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


def test_geo_cyclones_shape():
    r = client.get("/geo/cyclones")
    assert r.status_code == 200
    body = r.json()
    assert body["geojson"]["type"] == "FeatureCollection"
    assert "provenance" in body


def test_geo_sst_grid():
    r = client.get("/geo/sst-grid", params={"minlon": 73.0, "minlat": 14.0, "maxlon": 75.0, "maxlat": 16.0, "n": 3})
    assert r.status_code == 200
    cells = r.json()["data"]["cells"]
    assert len(cells) == 9 and all("sst" in c for c in cells)


def test_geo_chl_mocked(monkeypatch):
    from backend.app.api import geo as geo_mod

    monkeypatch.setattr(geo_mod.satellite, "fetch_chl", lambda *a, **k: {"png": b"PNG", "bounds": [], "cached": False})
    r = client.get("/geo/chl", params={"minlon": 73.9, "minlat": 14.9, "maxlon": 74.1, "maxlat": 15.1})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_cap_parse_offline():
    from backend.app.data import cyclones as cy

    xml = open("data/fixtures/cap_alerts.json").read()
    assert "polygon" in xml  # fixture carries sampled shape
    sample = (
        "<alert><info><event>Test</event><severity>Moderate</severity>"
        "<headline>H</headline><areaDesc>A</areaDesc><expires>E</expires>"
        "<polygon>10.0,70.0 11.0,71.0 10.0,71.0 10.0,70.0</polygon></info></alert>"
    )
    a = cy._parse_alert(sample)
    assert a["polygon"][0] == [70.0, 10.0]  # GeoJSON lon,lat order
    assert cy.as_geojson([a])["features"][0]["geometry"]["type"] == "Polygon"
