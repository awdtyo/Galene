"""Phase 4: RAG retrieval grounds answers with citations."""

from backend.app.rag.store import retrieve


def test_retrieve_thresholds():
    hits = retrieve("wind wave unsafe limits small craft")
    assert hits and hits[0]["title"] == "safety_thresholds"


def test_retrieve_geofence():
    hits = retrieve("EEZ MPA boundary navigation disclaimer")
    assert any(h["title"] == "geofence_disclaimer" for h in hits)


def test_answers_carry_citations(monkeypatch):
    from fastapi.testclient import TestClient

    from backend.app.config import settings
    from backend.app.main import app

    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    r = TestClient(app).post("/ask", json={"query": "Is it safe tomorrow morning?"})
    assert r.json()["citations"], "expected RAG citations"
