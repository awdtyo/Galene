"""Phase 3 end-to-end: safety query -> verdict + reasons + full trace. Offline via mock LLM."""

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)


def test_safety_query_end_to_end(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    r = client.post("/ask", json={"query": "Is it safe tomorrow morning?", "lat": 15.0, "lon": 74.0})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in ("safe", "caution", "unsafe")
    assert len(body["reasons"]) > 0 and len(body["answer"]) > 0
    agents = [t["agent"] for t in body["trace"]]
    for expected in ("planner", "weather", "risk", "viz"):
        assert expected in agents, agents
    assert any(t["tool"] == "get_forecast" for t in body["trace"])


def test_risk_rules_deterministic():
    from backend.app.agents import risk

    trace: list = []
    out = risk.verdict({"max_wind_kmh": 70, "max_wave_m": 5.0, "warnings": []}, trace)
    assert out["verdict"] == "unsafe"
    trace2: list = []
    out2 = risk.verdict({"max_wind_kmh": 10, "max_wave_m": 0.5, "warnings": [{"warning": "No warning"}]}, trace2)
    assert out2["verdict"] == "safe"
