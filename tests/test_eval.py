"""Phase 6 English-only eval set (product-goal queries). Shape assertions, mock LLM."""

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)

QUERIES = [
    ("Where is the nearest Potential Fishing Zone today?", {"lat": 15.0, "lon": 74.0}),
    ("Is it safe to go to sea tomorrow morning?", {"lat": 15.0, "lon": 74.0}),
    ("Tide, weather, and sea conditions near my fishing location?", {"lat": 15.0, "lon": 74.0}),
    ("Any cyclone alerts in my area?", {"lat": 13.0, "lon": 80.2}),
    ("Regions with high chlorophyll and favourable SST?", {"lat": 15.0, "lon": 74.0}),
    ("Safest route for a fishing vessel?", {"lat": 21.9, "lon": 88.0, "dest_lat": 21.9, "dest_lon": 89.4}),
    ("Why has fish productivity declined in this coastal region?", {"lat": 15.0, "lon": 74.0}),
    ("Which zones to avoid?", {"lat": 21.965, "lon": 88.91}),
]


def test_eval_shape(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    for q, loc in QUERIES:
        r = client.post("/ask", json={"query": q, **loc})
        assert r.status_code == 200, q
        b = r.json()
        assert b["answer"] and b["trace"] and b["citations"], q
        assert b["verdict"] in ("safe", "caution", "unsafe", "info"), q
        agents = {t["agent"] for t in b["trace"]}
        assert {"planner", "viz"} <= agents, q


def test_eval_safety_carries_geofence(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    r = client.post("/ask", json={"query": "Is it safe to go to sea tomorrow morning?", "lat": 15.0, "lon": 74.0})
    assert "Geofence" in r.json()["answer"]
