"""Memory facts — extraction persistence + semantic recall (Feature 13).

Facts the lead states (service wanted, budget, timeline, preference) are stored
in `memory_facts` with a 768-dim embedding, and recalled to prime the agent so
it never re-asks what it already knows.

Degrades gracefully:
  * Embeddings are produced via Gemini (`GEMINI_EMBED_MODEL`). If that's
    unavailable, facts are still stored (embedding NULL) and recall falls back to
    most-recent active facts — the agent keeps working without pgvector.
  * Vector search is used only when both pgvector and an embedding are available.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import MemoryFact

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"service", "budget", "timeline", "preference", "other"}

# Is pgvector's SQLAlchemy type active on the model? (matches models/database.py guard)
try:  # pragma: no cover
    from pgvector.sqlalchemy import Vector as _Vector  # noqa: F401
    _HAS_PGVECTOR = True
except ImportError:  # pragma: no cover
    _HAS_PGVECTOR = False

_embed_client = None


# --------------------------------------------------------------------------- #
# Embeddings
# --------------------------------------------------------------------------- #

def embed_text(text: str) -> Optional[list[float]]:
    """Return a 768-dim embedding for ``text`` via Gemini, or None on any failure."""
    text = (text or "").strip()
    if not text or not settings.GEMINI_API_KEY:
        return None
    global _embed_client
    try:
        if _embed_client is None:
            from google import genai  # lazy
            _embed_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        result = _embed_client.models.embed_content(
            model=settings.GEMINI_EMBED_MODEL,
            contents=text,
        )
        # SDK shape: result.embeddings -> [ContentEmbedding(values=[...])]
        embeddings = getattr(result, "embeddings", None)
        if embeddings:
            values = getattr(embeddings[0], "values", None) or embeddings[0]
            return list(values)
        emb = getattr(result, "embedding", None)
        if emb is not None:
            return list(getattr(emb, "values", None) or emb)
    except Exception as exc:
        logger.warning("embed_text failed: %s", exc)
    return None


# --------------------------------------------------------------------------- #
# Persist
# --------------------------------------------------------------------------- #

def add_memory_fact(
    db: Session,
    workspace_id: str,
    lead_id: str,
    *,
    fact: str,
    category: str = "other",
    confidence: int = 80,
    source: str = "stated",
) -> Optional[MemoryFact]:
    """Store one fact with dedup. Returns the row, or None if a near-duplicate
    already exists (same lead + category, substring match either direction)."""
    fact = (fact or "").strip()
    if not fact:
        return None
    category = (category or "other").lower().strip()
    if category not in VALID_CATEGORIES:
        category = "other"

    fact_lower = fact.lower()
    existing = (
        db.query(MemoryFact)
        .filter(
            MemoryFact.workspace_id == workspace_id,
            MemoryFact.lead_id == lead_id,
            MemoryFact.category == category,
            MemoryFact.is_active.is_(True),
        )
        .all()
    )
    for ex in existing:
        ex_lower = (ex.fact or "").strip().lower()
        if ex_lower and (fact_lower in ex_lower or ex_lower in fact_lower):
            logger.info("skip duplicate memory fact: %r (have %r)", fact, ex.fact)
            return None

    mf = MemoryFact(
        workspace_id=workspace_id,
        lead_id=lead_id,
        category=category,
        fact=fact,
        confidence=max(0, min(int(confidence or 0), 100)),
        source=(source or "stated").strip() or "stated",
    )
    embedding = embed_text(fact)
    if embedding is not None and _HAS_PGVECTOR:
        mf.embedding = embedding
    db.add(mf)
    db.flush()
    return mf


def store_facts(
    db: Session,
    workspace_id: str,
    lead_id: str,
    facts: list[dict[str, Any]],
) -> int:
    """Persist a list of extracted facts (as produced by the pipeline). Returns
    the count actually stored (after dedup). Each dict: {fact, category?,
    confidence?, source?}."""
    stored = 0
    for item in facts or []:
        if not isinstance(item, dict):
            continue
        text = (item.get("fact") or "").strip()
        if not text:
            continue
        row = add_memory_fact(
            db, workspace_id, lead_id,
            fact=text,
            category=item.get("category") or "other",
            confidence=int(item.get("confidence") or 80),
            source=item.get("source") or "stated",
        )
        if row is not None:
            stored += 1
    return stored


# --------------------------------------------------------------------------- #
# Recall
# --------------------------------------------------------------------------- #

def recall(
    db: Session,
    workspace_id: str,
    lead_id: str,
    query: Optional[str] = None,
    *,
    limit: int = 8,
) -> list[MemoryFact]:
    """Return the most relevant active facts for a lead. Uses pgvector cosine
    distance when a query embedding is available; otherwise most-recent first."""
    base = db.query(MemoryFact).filter(
        MemoryFact.workspace_id == workspace_id,
        MemoryFact.lead_id == lead_id,
        MemoryFact.is_active.is_(True),
    )

    if query and _HAS_PGVECTOR:
        vec = embed_text(query)
        if vec is not None:
            try:
                return (
                    base.filter(MemoryFact.embedding.isnot(None))
                    .order_by(MemoryFact.embedding.cosine_distance(vec))
                    .limit(limit)
                    .all()
                )
            except Exception as exc:
                logger.warning("vector recall failed, falling back to recency: %s", exc)

    return base.order_by(MemoryFact.created_at.desc()).limit(limit).all()


def build_memory_context(
    db: Session,
    workspace_id: str,
    lead_id: str,
    query: Optional[str] = None,
    *,
    limit: int = 8,
    max_chars: int = 1200,
) -> str:
    """Text block of recalled facts for prompt injection (empty string if none)."""
    facts = recall(db, workspace_id, lead_id, query, limit=limit)
    lines: list[str] = []
    total = 0
    for f in facts:
        line = f"- [{f.category}] {f.fact}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines)
