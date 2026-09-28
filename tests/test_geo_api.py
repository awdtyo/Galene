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
