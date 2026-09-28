"""Multi-turn memory: in-process session store. Single-instance demo baseline.

Limits (documented): process-local dict, capped at 50 sessions x 20 turns.
Multi-worker persistence is explicitly out of scope until later phases.
"""

import time

_MAX_SESSIONS, _MAX_TURNS = 50, 20
_sessions: dict[str, dict] = {}


def remember(session_id: str, role: str, text: str) -> None:
    if not session_id:
        return
    s = _sessions.setdefault(session_id, {"turns": [], "updated": 0.0})
    s["turns"].append({"role": role, "text": text[:2000]})
    s["turns"] = s["turns"][-_MAX_TURNS:]
    s["updated"] = time.time()
    if len(_sessions) > _MAX_SESSIONS:
        oldest = min(_sessions, key=lambda k: _sessions[k]["updated"])
        del _sessions[oldest]


def recall(session_id: str, n: int = 6) -> list[dict]:
    if not session_id:
        return []
    return _sessions.get(session_id, {}).get("turns", [])[-n:]


def clear(session_id: str) -> None:
    _sessions.pop(session_id, None)
