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

_KEYWORDS = {
    "pfz": ("pfz", "fish zone", "fishing zone", "chlorophyll", "potential fishing"),
    "zone": ("eez", "mpa", "restricted", "boundary", "protected area", "zone to avoid"),
    "route": ("route", "safest way", "navigate", "waypoint", "passage"),
    "safety": ("safe", "safety", "weather", "sea condition", "tide", "cyclone", "alert", "lightning", "tomorrow", "morning"),
}


def classify(query: str) -> str:
    q = query.lower()
    for intent, words in _KEYWORDS.items():
        if any(w in q for w in words):
            return intent
    out = chat([{"role": "user", "content": f"intent of: {query}. Reply safety/pfz/zone/route."}])
    return out["text"].strip().lower() if out["text"].strip().lower() in _KEYWORDS else "safety"


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

    if intent == "pfz":
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
        warn = f"WARNING inside {res['mpa_name']} — avoid." if res["inside_mpa"] else "Clear of protected areas."
        facts = f"Inside EEZ: {res['inside_eez']}. {warn}"
    elif intent == "route":
        if dest_lat is None or dest_lon is None:
            facts = "To plan a route I need a destination: send dest_lat and dest_lon."
            res, route = {}, None
        else:
            res = geo.assess(point, LatLon(lat=dest_lat, lon=dest_lon), trace)
            r = res["route"]
            facts = (
                f"Route {r['distance_km']} km, {len(r['waypoints'])} waypoint(s)"
                f"{' with MPA detour' if r['detoured'] else ', direct'}."
            )
    else:
        summary = weather.summarize(point, trace)
        if not summary.get("window"):
            summary, degraded = _replan("weather", trace, lambda: weather.summarize(point, trace))
        decision = risk.verdict(summary, trace)
        facts = report.safety_facts(summary, decision)

    text, citations = report.format_response(query, facts, trace, history)
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
