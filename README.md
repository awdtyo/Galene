# ORCA — Marine EcOsystem Reasoning with Collaborative Agents

Agentic, conversational marine intelligence platform for fishermen,
researchers, and coastal authorities.

> Phase 0 skeleton only. No agent/tool logic yet.
> See `AGENTS.md` for working rules and `docs/architecture.md` for design.

## Quickstart (Phase 0)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn backend.app.main:app --reload
pytest
```

- Health check: `GET /health`
- `POST /ask` is a Phase 0 stub and returns `501 Not Implemented`.
  Full implementation lands in Phase 3+.

## Repo layout

- `backend/app/` — FastAPI entry, config, logging, api schemas
- `frontend/` — static Leaflet + chat placeholder (real UI in Phase 5)
- `data/fixtures/` — offline mock JSON (starts Phase 1)
- `data/cache/` — runtime cache, gitignored
- `docs/` — architecture notes
- `tests/` — pytest suite
