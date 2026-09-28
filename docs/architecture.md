# ORCA Architecture (Phase 0)

Python + FastAPI backend, static web frontend (Leaflet + chat UI).

```
User -> Frontend (chat + map) -> POST /ask -> Planner/Orchestrator
  -> Data Discovery -> Weather/Hazard, Ocean Analytics,
     Geospatial, Risk (deterministic) -> Viz/Report -> Response + trace
```

## Agents (each a module with a clear tool interface)

- Planner/Orchestrator: intent parsing, decomposition, routing, replanning
- Data Discovery: choose/fetch datasets
- Weather/Hazard: cyclone, lightning, wave/wind alerts
- Ocean Analytics: SST, chlorophyll, fronts, PFZ, trends
- Geospatial: nearest-zone, geofencing, routing
- Risk: rule-based safe/caution/unsafe verdict
- Viz/Report: maps, charts, advisories, evidence trace + single
  format_response() step (all user-facing text passes through here;
  future language layer plugs in here only)

## Principles

- No training. Pretrained LLM + function calling + typed tools.
- Risk + geofence are deterministic (rules/geometry).
- RAG over advisories/guidelines/regulations grounds explanations (Phase 4).
- Every response carries evidence + reasoning trace:
  agents ran, tools called, data used, timestamps (schema from Phase 3).
- Every data tool has cached/mock fallback for offline demo (Phase 1+).
