"""Phase 4: memory roundtrip across turns (offline via mock LLM)."""

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.memory import clear, recall

client = TestClient(app)


def test_memory_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    sid = "test-session-1"
    clear(sid)
    client.post("/ask", json={"query": "Is it safe tomorrow morning?", "session_id": sid})
    r = client.post("/ask", json={"query": "What about PFZ zones?", "session_id": sid})
    assert r.status_code == 200
    assert r.json()["session_id"] == sid
    turns = recall(sid)
    assert len(turns) >= 4  # 2 user + 2 assistant
    clear(sid)
    assert recall(sid) == []
