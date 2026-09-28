"""File cache + fixture fallback. Every fetcher uses this; demo works offline."""

import json
import time
from pathlib import Path

from backend.app.config import settings


def _dir(kind: str) -> Path:
    base = settings.DATA_CACHE_DIR if kind == "cache" else settings.DATA_FIXTURES_DIR
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_path(name: str) -> Path:
    return _dir("cache") / f"{name}.json"


def fixture_path(name: str) -> Path:
    return _dir("fixtures") / f"{name}.json"


def read_cache(name: str, ttl_s: int = 3600) -> dict | None:
    p = cache_path(name)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text())
        if time.time() - payload.get("_cached_at", 0) > ttl_s:
            return None
        return payload.get("data")
    except (OSError, ValueError):
        return None


def write_cache(name: str, data: dict) -> None:
    try:
        cache_path(name).write_text(json.dumps({"_cached_at": time.time(), "data": data}))
    except OSError:
        pass  # cache is best-effort; fixtures still work


def read_fixture(name: str) -> dict:
    return json.loads(fixture_path(name).read_text())


def provenance(source: str, mode: str) -> dict:
    return {
        "source": source,
        "mode": mode,  # live | cache | fixture
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
