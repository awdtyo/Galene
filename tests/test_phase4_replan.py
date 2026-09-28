"""Phase 4: multi-intent routing + replan flag (offline via mock LLM)."""

from fastapi.testclient import TestClient

from backend.app.agents.planner import classify
from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)


def test_classify_intents():
    assert classify("Where is the nearest PFZ today?") == "pfz"
    assert classify("Which zones to avoid near the MPA?") == "zone"
    assert classify("Safest route for my vessel?") == "route"
    assert classify("Is it safe tomorrow morning?") == "safety"
    assert classify("Compare Kochi vs Chennai tomorrow?") == "compare"
    assert classify("Am I in a restricted fishing zone?") == "zone"


def test_pfz_zone_route_branches(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    r = client.post("/ask", json={"query": "Regions with high chlorophyll and PFZ?"})
    assert r.status_code == 200 and "PFZ" in r.json()["answer"]
    r = client.post("/ask", json={"query": "Am I inside a restricted MPA zone?", "lat": 15.0, "lon": 74.0})
    assert "EEZ" in r.json()["answer"]
    r = client.post("/ask", json={"query": "Plan a route", "lat": 15.0, "lon": 74.0})
    assert "destination" in r.json()["answer"].lower()
    r = client.post(
        "/ask",
        json={"query": "Safest route?", "lat": 21.9, "lon": 88.0, "dest_lat": 21.9, "dest_lon": 89.4},
    )
    assert "detour" in r.json()["answer"].lower() or "Route" in r.json()["answer"]


def test_degraded_flag_present(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    r = client.post("/ask", json={"query": "Is it safe tomorrow morning?"})
    assert "degraded" in r.json()


def test_compare_branch(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    r = client.post("/ask", json={"query": "Compare Kochi vs Chennai tomorrow?"})
    assert r.status_code == 200
    b = r.json()
    assert "Calmer choice" in b["answer"] and "Kochi" in b["answer"] and "Chennai" in b["answer"]
    r = client.post("/ask", json={"query": "Compare Kochi tomorrow?"})
    assert "name two sites" in r.json()["answer"]
