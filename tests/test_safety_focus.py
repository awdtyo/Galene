"""Query-specific safety answers: same location, different focus -> different lead facts."""

from fastapi.testclient import TestClient

from backend.app.agents.planner import safety_focus
from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)
LOC = {"lat": 15.0, "lon": 74.0}


def _ask(q):
    return client.post("/ask", json={"query": q, **LOC}).json()


def test_safety_focus_parser():
    assert safety_focus("What are the tide times?") == "tide"
    assert safety_focus("Any cyclone alerts?") == "alerts"
    assert safety_focus("How strong is the wind?") == "wind"
    assert safety_focus("Wave height today?") == "wave"
    assert safety_focus("Is it safe tomorrow morning?") == "general"


def test_query_specific_leads(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    tide = _ask("What are the tide times tomorrow morning?")["answer"]
    cyclone = _ask("Any cyclone alerts in my area?")["answer"]
    wind = _ask("How strong is the wind tomorrow?")["answer"]
    wave = _ask("What is the wave height tomorrow?")["answer"]
    general = _ask("Is it safe to go to sea tomorrow morning?")["answer"]

    assert tide.startswith("High tide") or "High tide" in tide.split(".")[0]
    assert "Warnings:" in cyclone.split(".")[0]
    assert "Wind focus" in wind
    assert "Wave focus" in wave
    # Same location must not return identical answers
    assert len({tide, cyclone, wind, wave, general}) == 5
    # Shape preserved for all
    for a in (tide, cyclone, wind, wave, general):
        assert "Geofence" in a
        assert "km/h" in a or " m" in a
