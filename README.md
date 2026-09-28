# ORCA — Marine EcOsystem Reasoning with Collaborative Agents

Agentic, conversational marine intelligence platform for fishermen,
researchers, and coastal authorities. English-only Q&A with explainable,
evidence-backed recommendations: safety verdicts, PFZ outlook, geofence
warnings, and routing — with maps, alerts, and a full reasoning trace.

> See `AGENTS.md` for working rules, `docs/architecture.md` for design,
> `docs/data_sources.md` for the verified source audit, `docs/demo.md` for the demo script.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # fill ORCA_LLM_API_KEY (Groq) + Copernicus creds; never commit
uvicorn backend.app.main:app --reload
pytest                       # 32 tests, offline-safe (mock fallbacks)
```

- `GET /health` — status + LLM provider
- `POST /ask` — `{query, lat, lon, session_id?, dest_lat?, dest_lon?}` →
  `{answer, verdict, reasons, trace, citations, degraded}`
- `GET /geo/eez`, `/geo/mpas`, `/geo/pfz` — real simplified polygons/zones for the map
- UI: serve `frontend/` statically (e.g. `python3 -m http.server`) + open `index.html`
- Alerts CLI: `python3 scripts/check_alerts.py [--mock]`

## Repo layout

- `backend/app/` — FastAPI entry, swappable-LLM config (`mock` default, Groq live), logging
- `backend/app/agents/` — planner, weather, risk (deterministic), ocean, geo, discovery, report
- `backend/app/tools/` — 8 typed tools (forecast, tides, alerts, SST, chlorophyll, PFZ, geofence, route)
- `backend/app/data/` — thin fetchers (Open-Meteo live; IMD/INCOIS/Copernicus keyed/fixture) with cache + fixtures
- `backend/app/rag/` — TF-IDF-grounded advisory corpus (wording only, never the verdict)
- `backend/app/memory.py` — multi-turn session store
- `frontend/` — dependency-free Leaflet chat + map (EEZ/MPA/PFZ layers), alert badge, trace viewer
- `data/fixtures/` — offline JSON incl. real simplified EEZ (MarineRegions, CC-BY) + 6 WDPA MPAs
- `data/cache/` — runtime cache, gitignored
- `docs/` — architecture, data-source audit, demo script
- `scripts/` — proactive alerts watchlist CLI
- `tests/` — pytest suite incl. English-only eval set
