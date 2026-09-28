"""ORCA FastAPI entry. Phase 0: /health live, /ask stub only."""

import logging
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.app.api.schemas import AskRequest
from backend.app.config import settings
from backend.app.logging_conf import setup_logging

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("orca")

app = FastAPI(title="ORCA", version="0.1.0")


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
def ask(_body: AskRequest):
    # Full planner + agents land in Phase 3. Stub keeps contract visible.
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented in Phase 0. See Phase 3."},
    )
