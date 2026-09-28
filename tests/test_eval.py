"""Phase 6 English-only eval set (product-goal queries). Shape assertions, mock LLM."""

import re

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)
NUMBER_WITH_UNIT = re.compile(r"\d+(\.\d+)?\s?(km/h|m\b|C\b|mg/m3|km\b)")

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


def test_eval_answers_have_numbers_and_terms(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    for q, loc in QUERIES:
        b = client.post("/ask", json={"query": q, **loc}).json()
        assert NUMBER_WITH_UNIT.search(b["answer"]), q
        assert "Protected Fishing Zone" not in b["answer"], q


def test_eval_zone_reports_nearest_mpa(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    b = client.post("/ask", json={"query": "Which zones to avoid?", "lat": 15.0, "lon": 74.0}).json()
    assert "Nearest MPA" in b["answer"] and "km away" in b["answer"]


def test_terminology_corpus_retrieved():
    from backend.app.rag.store import retrieve

    titles = [h["title"] for h in retrieve("What does PFZ stand for?")]
    assert "terminology" in titles  # grounds exact acronym expansions
