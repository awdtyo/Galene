from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.content is not None
    assert r.json()["status"] == "ok"


def test_ask_stub_returns_501():
    r = client.post("/ask", json={"query": "Is it safe tomorrow morning?"})
    assert r.status_code == 501
