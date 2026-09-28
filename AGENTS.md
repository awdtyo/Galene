# AGENTS.md — ORCA Working Rules & Constraints

This file is authoritative for all agents working in this repo.
It captures the user's WORKING RULES verbatim, plus derived conventions.

## 1. Working rules (highest priority, verbatim)

1. Work in PHASES. At the end of each phase, STOP and wait for the user
   to say "confirm" before starting the next one.
2. Before writing or changing any files in a phase, first show a short
   plan: files to create/modify, key design choices, and anything unsure.
   Wait for approval, then implement.
3. Do not install packages, run destructive commands, or modify files
   outside this repo without asking first.
4. Never fabricate data-source URLs, API endpoints, or dataset schemas.
   If unsure an endpoint exists or how it behaves, say so and verify it
   (fetch/test it) or mark it as TODO. Every data tool needs a cached/mock
   fallback so the demo works offline.
5. Keep things simple and modular. No premature abstraction. Write tests
   for each tool as you go.
6. Every answer the system produces must carry its evidence and reasoning
   trace (which agents ran, which tools, which data, timestamps).

## 2. Product constraints

- English-only marine Q&A for now. Multilingual support is OUT OF SCOPE.
  No Language agent, no detection / same-language reply requirement.
- No translation or language-detection dependencies.
- All user-facing text must pass through a single response-formatting step
  in the Viz/Report agent, so a language layer can be added later without
  touching the other agents. Do not build that layer now.
- Deterministic risk verdicts and geofencing (rules + geometry), not ML.
- No model training. Pretrained LLM with function calling + typed tools.
- LLM provider must be swappable via config/env. Never hardcode one.
- Small RAG layer over advisories/guidelines/regulations (Phase 4).
- Prefer real public sources (INCOIS, IMD, Copernicus Marine, GEBCO,
  EEZ/MPA boundaries). Verify access before relying on them (Phase 1).

## 3. Engineering conventions (Phase 0)

- Python 3.11+, FastAPI backend, static HTML + Leaflet frontend.
- Config via env + `backend/app/config.py` (pydantic-settings).
  Default `ORCA_LLM_PROVIDER=mock` so the demo works offline.
- Logging via stdlib `logging` + `backend/app/logging_conf.py`.
  Every request logs with request ID and timestamp. Reasoning-trace
  model itself is added in Phase 3.
- Data fetchers (Phase 1+) must support `cache/` + `fixtures/` fallback.
- Tools (Phase 2+) are typed functions with pytest coverage.
- Frontend (Phase 5) stays dependency-free (no build step) for now.
  No language switcher (English-only; Phase 6 eval set is English-only).
- Do not add new dependencies without user approval.

## 4. Phase gate

End every phase with: what was done, what is TODO/uncertain, and STOP
until the user replies "confirm".
