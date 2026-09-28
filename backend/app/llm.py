"""Swappable LLM chat client. `mock` works offline; `groq` hits the
OpenAI-compatible chat endpoint from settings. No new deps (httpx only)."""

import httpx

from backend.app.config import settings

SYSTEM = "You are ORCA, a marine safety assistant. Reply in English, briefly."


def chat(messages: list[dict], *, system: str = SYSTEM) -> dict:
    """Return {text, provenance}. Deterministic mock unless provider=groq."""
    provider, model, base_url = settings.resolved_llm()
    if provider != "groq" or not settings.LLM_API_KEY.strip():
        return {"text": _mock(messages), "provider": "mock"}
    try:
        r = httpx.post(
            base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY.strip()}"},
            json={"model": model, "messages": [{"role": "system", "content": system}, *messages], "temperature": 0.2},
            timeout=30,
        )
        r.raise_for_status()
        return {"text": r.json()["choices"][0]["message"]["content"], "provider": "groq"}
    except Exception:
        return {"text": _mock(messages), "provider": "mock-fallback"}


def _mock(messages: list[dict]) -> str:
    last = messages[-1]["content"] if messages else ""
    if "intent" in last.lower():
        return "safety"
    return f"Mock advisory basis: {last[:160]}"
