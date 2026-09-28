"""Small RAG store: stdlib TF-IDF cosine retrieval over rag/corpus/*.md.

Baseline only (vector DB deferred). Every passage carries its source URL
inline; retrieve() returns top-k {title, snippet, score}. No new deps.
"""

import math
import re
from pathlib import Path

_CORPUS = Path(__file__).parent / "corpus"
_docs: list[dict] | None = None


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z]{2,}", s.lower())


def _load() -> list[dict]:
    global _docs
    if _docs is None:
        _docs = []
        for p in sorted(_CORPUS.glob("*.md")):
            text = p.read_text()
            tf: dict[str, int] = {}
            for t in _tokens(text):
                tf[t] = tf.get(t, 0) + 1
            _docs.append({"title": p.stem, "text": text, "tf": tf})
    return _docs


def retrieve(query: str, k: int = 2) -> list[dict]:
    docs = _load()
    qt = _tokens(query)
    if not qt:
        return []
    df: dict[str, int] = {}
    for t in set(qt):
        df[t] = sum(1 for d in docs if t in d["tf"])
    scored = []
    for d in docs:
        s = sum(d["tf"].get(t, 0) * math.log(1 + len(docs) / (1 + df[t])) for t in qt)
        if s > 0:
            scored.append({"title": d["title"], "snippet": d["text"][:400], "score": round(s, 3)})
    return sorted(scored, key=lambda x: -x["score"])[:k]
