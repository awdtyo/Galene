"""Viz/Report agent: single format_response() for ALL user-facing text.

RAG citations ground wording only — never the deterministic verdict.
"""

from backend.app.api.schemas import now_iso
from backend.app.llm import SKY_SYSTEM, chat
from backend.app.rag.store import retrieve


def format_response(
    query: str, facts: str, trace: list, history: list | None = None, focus: str = "general"
) -> tuple[str, list[str]]:
    """Return (answer, citation_titles). Single exit point for user-facing text.

    Fixed template: Verdict -> Numbers -> Geofence -> What-to-do -> Sources.
    `focus` (tide|alerts|wind|wave|sky|general) reorders which numbers lead so
    live-LLM phrasing stays query-specific; mock path returns facts verbatim.
    Target length 250-300 words for live phrasing (see llm.SYSTEM).
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
        "sky": "Lead Key numbers with cloud cover %, visibility km, and weather-code meaning for tonight. "
        "Do NOT lead with wind/wave; this is a night-sky clarity question. ",
    }.get(focus, "")
    out = chat(
        [
            {
                "role": "user",
                "content": (
                    "Write the advisory with these sections: Verdict, Key numbers, "
                    f"Geofence, What-to-do. {emphasis}Focus: {focus}. "
                    f"Target 250-300 words. Facts: {facts}.{hist} Guidance: {ctx}"
                ),
            }
        ],
        system=SKY_SYSTEM if focus == "sky" else None,
    ) if focus == "sky" else chat(
        [
            {
                "role": "user",
                "content": (
                    "Write the advisory with these sections: Verdict, Key numbers, "
                    f"Geofence, What-to-do. {emphasis}Focus: {focus}. "
                    f"Target 250-300 words. Facts: {facts}.{hist} Guidance: {ctx}"
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


_WMO = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "rain",
    65: "heavy rain",
    80: "light showers",
    81: "showers",
    82: "violent showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with hail",
}


def _wmo_text(code: int | None) -> str | None:
    if code is None:
        return None
    if code in _WMO:
        return _WMO[code]
    if 71 <= code <= 77:
        return "snow"
    if 85 <= code <= 86:
        return "snow showers"
    return f"WMO code {code}"


def sky_reasons(sky: dict) -> list[str]:
    """Info-only reasons for night-sky clarity. No risk verdict."""
    reasons = []
    if sky.get("avg_cloud_pct") is not None:
        c = sky["avg_cloud_pct"]
        if c < 20:
            reasons.append(f"Average cloud cover {c:.0f}% — sky mostly clear, moon likely visible.")
        elif c < 60:
            reasons.append(f"Average cloud cover {c:.0f}% — partly cloudy, moon may appear in breaks.")
        else:
            reasons.append(f"Average cloud cover {c:.0f}% — mostly cloudy, moon likely obscured.")
    if sky.get("min_visibility_km") is not None:
        reasons.append(f"Minimum visibility {sky['min_visibility_km']:.1f} km over {sky['window']}.")
    codes = sky.get("weather_codes") or []
    if codes:
        dom = max(set(codes), key=codes.count)
        txt = _wmo_text(dom)
        if txt:
            reasons.append(f"Most frequent condition: {txt}.")
    if not reasons:
        reasons.append("Night-sky model data unavailable for this window; check local sky before relying on moonlight.")
    return reasons


def sky_facts(sky: dict, point) -> str:
    """250-300 word mock-safe sky advisory. Leads with cloud/visibility, never wind/wave."""
    lat = getattr(point, "lat", point.get("lat") if isinstance(point, dict) else "?")
    lon = getattr(point, "lon", point.get("lon") if isinstance(point, dict) else "?")
    cloud = sky.get("avg_cloud_pct")
    vis = sky.get("min_visibility_km")
    codes = sky.get("weather_codes") or []
    dom_txt = _wmo_text(max(set(codes), key=codes.count)) if codes else None
    if cloud is not None and cloud < 20:
        verdict_line = "[INFO] Moon likely visible tonight — sky mostly clear."
    elif cloud is not None and cloud < 60:
        verdict_line = "[INFO] Moon may appear in breaks tonight — partly cloudy."
    elif cloud is not None:
        verdict_line = "[INFO] Moon likely obscured tonight — mostly cloudy."
    else:
        verdict_line = "[INFO] Night-sky outlook for tonight — limited cloud data."
    numbers = []
    if cloud is not None:
        numbers.append(f"average cloud cover {cloud:.0f}%")
    if vis is not None:
        numbers.append(f"minimum visibility {vis:.1f} km")
    if dom_txt:
        numbers.append(f"most frequent condition {dom_txt}")
    numbers_txt = (", ".join(numbers) + f" over {sky['window']} ({sky.get('n_hours', '?')} hourly values)") if numbers else (
        f"model cloud and visibility values were not available for {sky['window']}, so this outlook is cautious"
    )
    return (
        f"{verdict_line} Window {sky['window']} near lat {lat}, lon {lon}: {numbers_txt}. "
        f"Reasons: {'; '.join(sky_reasons(sky))} "
        "What this means for you: a low cloud percentage means more of the night sky stays open, so the moon and bright stars "
        "remain easy to spot, while a high percentage means clouds cover most of the sky and the moon may glow faintly through haze "
        "or disappear entirely behind thick layers. Visibility distance tells a complementary story, because haze, mist, fog, drizzle, "
        "or nearby showers can dim the moon even when overhead clouds look thin, especially close to the coast where humidity rises after sunset. "
        "If the most frequent condition mentions fog, drizzle, rain, showers, or thunderstorm, treat the moon as unlikely to stay clearly visible for long, "
        "and plan any moonlit work, night navigation, or sky watching around the clearer breaks rather than a fixed hour. "
        "Practical steps: check the sky again shortly before heading out, since night clouds can clear or build within an hour; prefer a dark spot away from "
        "harbour and town lights for the clearest view; carry a reliable light even on a clear moonlit night because decks stay slippery and shared waterways need signals; "
        "and if fishing overnight, weigh this sky note alongside the separate sea-safety factors of wind, waves, and official warnings before deciding to sail."
    )
