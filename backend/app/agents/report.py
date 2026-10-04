"""Viz/Report agent: single format_response() for ALL user-facing text.

RAG citations ground wording only — never the deterministic verdict.
"""

from backend.app.api.schemas import now_iso
from backend.app.llm import chat
from backend.app.rag.store import retrieve


def format_response(
    query: str, facts: str, trace: list, history: list | None = None, focus: str = "general"
) -> tuple[str, list[str]]:
    """Return (answer, citation_titles). Single exit point for user-facing text.

    Fixed template: Verdict -> Numbers -> Geofence -> What-to-do -> Sources.
    `focus` (tide|alerts|wind|wave|general) reorders which numbers lead so
    live-LLM phrasing stays query-specific; mock path returns facts verbatim.
    """
    cites = retrieve(query)
    ctx = " ".join(c["snippet"][:200] for c in cites)
    hist = ""
    if history:
        hist = " Conversation so far: " + " | ".join(f"{t['role']}: {t['text'][:120]}" for t in history[-4:])
    emphasis = {
        "tide": "Lead Key numbers with tide times/heights, then wind/wave verdict briefly. ",
        "alerts": "Lead Key numbers with warnings/cyclone status, then wind/wave. ",
        "wind": "Lead Key numbers with wind, then wave/tide briefly. ",
        "wave": "Lead Key numbers with wave height, then wind/tide briefly. ",
    }.get(focus, "")
    out = chat(
        [
            {
                "role": "user",
                "content": (
                    "Write the advisory with these sections: Verdict, Key numbers, "
                    f"Geofence, What-to-do. {emphasis}Focus: {focus}. "
                    f"Facts: {facts}.{hist} Guidance: {ctx}"
                ),
            }
        ]
    )
    trace.append({"agent": "viz", "tool": f"llm:{out['provider']}", "timestamp": now_iso()})
    titles = [c["title"] for c in cites]
    suffix = f" Sources: {', '.join(titles)}." if titles else ""
    if out["provider"].startswith("mock"):
        return f"{facts}.{suffix}", titles
    text = out["text"] if "Sources:" in out["text"] else f"{out['text']}\n\nSources: {', '.join(titles)}."
    return text, titles


def safety_facts(summary: dict, decision: dict) -> str:
    return safety_facts_focused(summary, decision, focus="general")


def safety_facts_focused(summary: dict, decision: dict, focus: str = "general") -> str:
    """Query-specific fact ordering. Tide/alerts/wind/wave lead; verdict kept."""
    base = (
        f"[{decision['verdict'].upper()}] Window {summary['window']}: "
        f"max wind {summary['max_wind_kmh']} km/h, max wave {summary['max_wave_m']} m. "
        f"Reasons: {'; '.join(decision['reasons'])}"
    )
    warnings = summary.get("warnings") or []
    warn_txt = "; ".join(str(w.get("warning", w)) for w in warnings) if warnings else "No warning"
    tide_txt = (
        f"High tide {summary.get('high_tide')}, low tide {summary.get('low_tide')}"
        + (f", height {summary.get('tide_height_m')} m" if summary.get("tide_height_m") is not None else "")
    )
    if focus == "tide":
        return f"{tide_txt}. {base}"
    if focus == "alerts":
        return f"Warnings: {warn_txt}. {base} {tide_txt}."
    if focus == "wind":
        return f"Wind focus: max wind {summary['max_wind_kmh']} km/h in {summary['window']}. {base}"
    if focus == "wave":
        return f"Wave focus: max wave {summary['max_wave_m']} m in {summary['window']}. {base}"
    return base
