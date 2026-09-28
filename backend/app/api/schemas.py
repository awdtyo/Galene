"""API schemas. Phase 3: verdict + reasons + timestamped trace."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    lat: float | None = None
    lon: float | None = None
    session_id: str | None = None
    dest_lat: float | None = None
    dest_lon: float | None = None


class TraceStep(BaseModel):
    agent: str
    tool: str | None = None
    timestamp: str


class AskResponse(BaseModel):
    answer: str
    verdict: str = "unknown"
    reasons: list[str] = []
    trace: list[TraceStep] = []
    session_id: str | None = None
    citations: list[str] = []
    degraded: bool = False
