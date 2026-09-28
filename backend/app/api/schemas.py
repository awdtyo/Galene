"""API schemas. Reasoning-trace model is expanded in Phase 3."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    lat: float | None = None
    lon: float | None = None


class TraceStep(BaseModel):
    agent: str
    tool: str | None = None
    timestamp: str


class AskResponse(BaseModel):
    answer: str
    trace: list[TraceStep] = []
