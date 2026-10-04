"""Swappable LLM chat client. `mock` works offline; `groq` hits the
OpenAI-compatible chat endpoint from settings. No new deps (httpx only)."""

import httpx

from backend.app.config import settings

SYSTEM = (
    "You are ORCA, a marine advisory assistant. Reply in English with this structure: "
    "1) Verdict line, 2) Key numbers fact block (wind km/h, wave m, SST C, with values from Facts only), "
    "3) Geofence note, 4) What-to-do guidance (2-4 sentences of prose explaining what the numbers mean for a fisher), "
    "5) Sources line. Rules: use ONLY numbers given in Facts — never invent values; "
    "expand acronyms ONLY as: PFZ=Potential Fishing Zone, OSF=Ocean State Forecast, "
    "EEZ=Exclusive Economic Zone, MPA=Marine Protected Area, IMD=India Meteorological Department; "
    "omit any metric absent from Facts — never write N/A, Unknown, or guessed values; "
    "never emit an empty 'Wind:/Wave:/SST:' line — if a metric is absent from Facts, omit that line entirely; "
    "250-300 words."
)

SKY_SYSTEM = (
    "You are ORCA, a marine advisory assistant. Reply in English with this structure: "
    "1) Verdict line about moon visibility, 2) Key numbers fact block with ONLY cloud cover %, "
    "visibility km, and weather-code condition from Facts (never wind, wave, or SST here), "
    "3) Geofence note, 4) What-to-do guidance explaining what the sky numbers mean for seeing the moon, "
    "5) Sources line. Rules: use ONLY numbers given in Facts — never invent values; "
    "omit any metric absent from Facts — never write N/A, Unknown, guessed values, or empty lines; "
    "250-300 words."
)


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
