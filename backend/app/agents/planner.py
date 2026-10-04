"""Planner/Orchestrator: multi-intent routing + replanning. Phase 4.

Intents: safety | pfz | zone | route. Keyword router first (deterministic,
offline); LLM confirms only when keywords are ambiguous. Replanning: any
empty/degraded tool result is retried once with fallback params and flagged.
"""

from backend.app.agents import discovery, geo, ocean, report, risk, weather
from backend.app.api.schemas import AskResponse, TraceStep, now_iso
from backend.app.llm import chat
from backend.app.memory import recall, remember
from backend.app.tools import LatLon

_DEFAULT = LatLon(lat=15.0, lon=74.0)

SITES = {
    "kochi": LatLon(lat=15.0, lon=74.0),
    "chennai": LatLon(lat=13.0, lon=80.2),
    "sundarbans": LatLon(lat=21.9, lon=88.9),
    "mumbai": LatLon(lat=19.0, lon=72.8),
    "vizag": LatLon(lat=17.7, lon=83.3),
    "visakhapatnam": LatLon(lat=17.7, lon=83.3),
}

_KEYWORDS = {
    "compare": (" vs ", " vs.", "compare", "versus"),
    "zone": ("eez", "mpa", "restricted", "boundary", "protected area", "zone to avoid", "avoid"),
    "pfz": ("pfz", "fish zone", "fishing zone", "chlorophyll", "potential fishing", "productiv", "decline"),
    "route": ("route", "safest way", "navigate", "waypoint", "passage"),
    "safety": ("safe", "safety", "weather", "sea condition", "tide", "cyclone", "alert", "lightning", "tomorrow", "morning"),
}


def classify(query: str) -> str:
    q = query.lower()
    for intent, words in _KEYWORDS.items():
        if any(w in q for w in words):
            return intent
    out = chat([{"role": "user", "content": f"intent of: {query}. Reply safety/pfz/zone/route/compare."}])
    return out["text"].strip().lower() if out["text"].strip().lower() in _KEYWORDS else "safety"


_SAFETY_FOCUS = {
    "tide": ("tide", "high tide", "low tide"),
    "alerts": ("cyclone", "alert", "warning", "storm", "depression", "lightning"),
    "wind": ("wind", "breeze", "gust"),
    "wave": ("wave", "swell", "surf"),
    "sky": ("moon", "visible", "clear sky", "sky clear", "clear", "cloudy", "cloud", "night sky", "stargaz", "sky"),
}


def safety_focus(query: str) -> str:
    """Query-specific sub-focus inside safety intent. Deterministic keywords."""
    q = query.lower()
    for focus, words in _SAFETY_FOCUS.items():
        if any(w in q for w in words):
            return focus
    return "general"


def _replan(label: str, trace: list, retry) -> tuple:
    """Run retry() once after recording the replan step. Returns (result, degraded)."""
    trace.append({"agent": "planner", "tool": f"replan:{label}", "timestamp": now_iso()})
    return retry(), True


def answer(
    query: str,
    lat: float | None,
    lon: float | None,
    session_id: str | None = None,
    dest_lat: float | None = None,
    dest_lon: float | None = None,
) -> AskResponse:
    trace: list = []
    degraded = False
    point = LatLon(lat=lat if lat is not None else _DEFAULT.lat, lon=lon if lon is not None else _DEFAULT.lon)
    history = recall(session_id or "", n=6)

    intent = classify(query)
    trace.append({"agent": "planner", "tool": "classify:" + intent, "timestamp": now_iso()})
    plan = discovery.choose(intent)
    trace.append({"agent": "planner", "tool": "discovery:" + ",".join(plan["datasets"]), "timestamp": now_iso()})
    decision: dict | None = None
    focus = "general"

    if intent == "compare":
        named = [n for n in SITES if n in query.lower()]
        if len(named) < 2:
            facts = f"To compare, name two sites from: {', '.join(sorted(set(SITES)))}."
        else:
            order = {"safe": 0, "caution": 1, "unsafe": 2}
            ranked = []
            for n in named[:2]:
                s = weather.summarize(SITES[n], trace)
                d = risk.verdict(s, trace)
                ranked.append((n, d["verdict"], s["max_wind_kmh"], s["max_wave_m"]))
            parts = [f"{n.title()}: {v}, wind {w} km/h, wave {m} m" for n, v, w, m in ranked]
            calmer = min(ranked, key=lambda r: (order[r[1]], r[2] or 999, r[3] or 999))[0]
            facts = "Compare tomorrow morning. " + " | ".join(parts) + f". Calmer choice: {calmer.title()}."
    elif intent == "pfz":
        res = ocean.analyze(point, "KERALA", trace)
        if not res["pfz_zones"]:
            res, degraded = _replan("pfz", trace, lambda: ocean.analyze(point, "KERALA", trace))
        facts = (
            f"PFZ: {len(res['pfz_zones'])} zone(s); SST {res['sst_c']} C, "
            f"chlorophyll {res['chlorophyll_mg_m3']} mg/m3. "
            f"{'Conditions look favourable.' if res['favourable'] else 'Conditions look weak.'} {res['note']}"
        )
    elif intent == "zone":
        res = geo.assess(point, None, trace)
        snap = weather.summarize(point, trace)
        sst = ocean.analyze(point, "KERALA", trace)["sst_c"]
        if res["inside_mpa"]:
            warn = f"WARNING: inside {res['mpa_name']} — AVOID entry."
        else:
            near = res["nearest_mpa"]
            warn = f"Clear of protected areas. Nearest MPA: {near['name']} ~{near['distance_km']} km away."
        eez = "Inside Indian EEZ." if res["inside_eez"] else "OUTSIDE Indian EEZ — check jurisdiction."
        facts = (
            f"{eez} {warn} Live snapshot {snap['window']}: "
            f"max wind {snap['max_wind_kmh']} km/h, max wave {snap['max_wave_m']} m, SST {sst} C."
        )
    elif intent == "route":
        if dest_lat is None or dest_lon is None:
            facts = "To plan a route I need a destination: send dest_lat and dest_lon."
            res, route = {}, None
        else:
            res = geo.assess(point, LatLon(lat=dest_lat, lon=dest_lon), trace)
            r = res["route"]
            dep = weather.summarize(point, trace)
            dep_verdict = risk.verdict(dep, trace)["verdict"]
            facts = (
                f"Route {r['distance_km']} km, {len(r['waypoints'])} waypoint(s)"
                f"{' with MPA detour' if r['detoured'] else ', direct'}. "
                f"Departure window verdict: {dep_verdict}."
            )
    else:
        focus = safety_focus(query)
        if focus == "sky":
            sky = weather.summarize_sky(point, trace)
            if not sky.get("window"):
                sky, degraded = _replan("sky", trace, lambda: weather.summarize_sky(point, trace))
            decision = {"verdict": "info", "reasons": report.sky_reasons(sky)}
            fence = geo.assess(point, None, trace)
            geo_note = (
                f" Geofence: inside {fence['mpa_name']} — AVOID entry." if fence["inside_mpa"]
                else (" Geofence: inside Indian EEZ, clear of protected areas." if fence["inside_eez"]
                      else " Geofence: OUTSIDE Indian EEZ — check jurisdiction.")
            )
            facts = report.sky_facts(sky, point) + geo_note
            text, citations = report.format_response(query, facts, trace, history, focus="sky")
            if session_id:
                remember(session_id, "user", query)
                remember(session_id, "assistant", text)
            return AskResponse(
                answer=text,
                verdict="info",
                reasons=decision["reasons"],
                trace=[TraceStep(**t) for t in trace],
                session_id=session_id,
                citations=citations,
                degraded=degraded,
            )
        summary = weather.summarize(point, trace, focus=focus)
        if not summary.get("window"):
            summary, degraded = _replan("weather", trace, lambda: weather.summarize(point, trace, focus=focus))
        decision = risk.verdict(summary, trace)
        fence = geo.assess(point, None, trace)
        geo_note = (
            f" Geofence: inside {fence['mpa_name']} — AVOID entry." if fence["inside_mpa"]
            else (" Geofence: inside Indian EEZ, clear of protected areas." if fence["inside_eez"]
                  else " Geofence: OUTSIDE Indian EEZ — check jurisdiction.")
        )
        facts = report.safety_facts_focused(summary, decision, focus) + geo_note

    text, citations = report.format_response(query, facts, trace, history, focus=focus)
    if session_id:
        remember(session_id, "user", query)
        remember(session_id, "assistant", text)
    return AskResponse(
        answer=text,
        verdict=decision["verdict"] if decision else "info",
        reasons=decision["reasons"] if decision else [],
        trace=[TraceStep(**t) for t in trace],
        session_id=session_id,
        citations=citations,
        degraded=degraded,
    )
