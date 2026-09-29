"""ORCA FastAPI entry. Phase 3: /health + /ask (planner pipeline)."""

import logging
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request

from backend.app.api.schemas import AskRequest
from backend.app.config import settings
from backend.app.logging_conf import setup_logging

from backend.app.api.geo import router as geo_router

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("orca")

app = FastAPI(title="ORCA", version="0.1.0")
app.include_router(geo_router)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_ctx.get()
        return True


logging.getLogger().addFilter(_RequestIdFilter())


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_ctx.set(rid)
    logger.info("request %s %s", request.method, request.url.path)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.get("/health")
def health():
    return {"status": "ok", "llm_provider": settings.LLM_PROVIDER}


@app.post("/ask")
def ask(body: AskRequest):
    from backend.app.agents import planner

    return planner.answer(body.query, body.lat, body.lon, body.session_id, body.dest_lat, body.dest_lon)


# Serve the dependency-free Leaflet UI from the same origin (added for demo run).
from pathlib import Path  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
