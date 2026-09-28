"""Viz/Report agent: single format_response() for ALL user-facing text.

RAG citations ground wording only — never the deterministic verdict.
"""

from backend.app.api.schemas import now_iso
from backend.app.llm import chat
from backend.app.rag.store import retrieve


def format_response(query: str, facts: str, trace: list, history: list | None = None) -> tuple[str, list[str]]:
    """Return (answer, citation_titles). Single exit point for user-facing text."""
    cites = retrieve(query)
    ctx = " ".join(c["snippet"][:200] for c in cites)
    hist = ""
    if history:
        hist = " Conversation so far: " + " | ".join(f"{t['role']}: {t['text'][:120]}" for t in history[-4:])
    out = chat([{"role": "user", "content": f"Phrase as a short fisher advisory. Facts: {facts}.{hist} Guidance: {ctx}"}])
    trace.append({"agent": "viz", "tool": f"llm:{out['provider']}", "timestamp": now_iso()})
    titles = [c["title"] for c in cites]
    if out["provider"].startswith("mock"):
        suffix = f" Sources: {', '.join(titles)}." if titles else ""
        return f"{facts}.{suffix}", titles
    return out["text"], titles


def safety_facts(summary: dict, decision: dict) -> str:
    return (
        f"[{decision['verdict'].upper()}] Window {summary['window']}: "
        f"max wind {summary['max_wind_kmh']} km/h, max wave {summary['max_wave_m']} m. "
        f"Reasons: {'; '.join(decision['reasons'])}"
    )
