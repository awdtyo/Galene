"""Sky-clarity answers: moon queries lead with cloud/visibility, info-only."""

from fastapi.testclient import TestClient

from backend.app.agents.planner import safety_focus
from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)
LOC = {"lat": 15.0, "lon": 74.0}


def test_sky_focus_parser():
    assert safety_focus("Is the moon visible tonight?") == "sky"
    assert safety_focus("Will the sky be clear?") == "sky"
    assert safety_focus("Is it cloudy tonight?") == "sky"


def test_moon_query_is_sky_specific(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    b = client.post("/ask", json={"query": "Is the moon visible tonight?", **LOC}).json()
    assert b["verdict"] == "info"
    ans = b["answer"]
    assert "moon" in ans.lower()
    assert "Cloud" in ans or "cloud" in ans
    assert "Geofence" in ans  # trailing geo line preserved
    assert "N/A" not in ans and "Unknown" not in ans
    assert 150 <= len(ans.split()) <= 400  # mock facts carry 250-300 word body
    agents = [t["agent"] for t in b["trace"]]
    assert "weather" in agents and "viz" in agents


def test_moon_differs_from_safety(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    moon = client.post("/ask", json={"query": "Is the moon visible?", **LOC}).json()["answer"]
    safety = client.post("/ask", json={"query": "Is it safe tomorrow morning?", **LOC}).json()["answer"]
    assert moon != safety
    assert "max wind" in safety
    assert "wind" not in moon.split(".")[0].lower() or "cloud" in moon.lower()
