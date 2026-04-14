"""Context Store — persistent business memory for SpineAgent.

Stores decisions, patterns, rules, action results, and state snapshots
associated with spine objects.  Supports both structured queries (exact filters)
and semantic search (vector similarity via pgvector).
"""

from __future__ import annotations

import json
from datetime import datetime

from agent.db import get_connection
from agent.embeddings import get_embedding

# ── Public API ───────────────────────────────────────────────────────────────


async def add_entry(
    spine_object_id: str,
    entry_type: str,
    content: dict,
    source: str = "system",
) -> int:
    """Insert a new context entry with an auto-generated embedding.

    Returns the new row id.
    """
    text = _content_to_text(content)
    embedding = await get_embedding(text)

    async with await get_connection() as conn:
        row = await (
            await conn.execute(
                """
                INSERT INTO spine_agent.context_entries
                    (spine_object_id, entry_type, content, embedding, source)
                VALUES (%(sid)s, %(etype)s, %(content)s, %(emb)s::vector, %(source)s)
                RETURNING id
                """,
                {
                    "sid": spine_object_id,
                    "etype": entry_type,
                    "content": json.dumps(content),
                    "emb": str(embedding),
                    "source": source,
                },
            )
        ).fetchone()
    return row["id"]


async def search_semantic(
    query: str,
    limit: int = 5,
    spine_object_id: str | None = None,
    entry_type: str | None = None,
) -> list[dict]:
    """Semantic search over context entries using vector cosine distance.

    Returns entries ordered by similarity (most similar first), with a
    ``similarity`` score between 0 and 1.
    """
    query_embedding = await get_embedding(query)

    where_parts: list[str] = []
    params: dict = {"emb": str(query_embedding), "lim": limit}

    if spine_object_id is not None:
        where_parts.append("spine_object_id = %(sid)s")
        params["sid"] = spine_object_id
    if entry_type is not None:
        where_parts.append("entry_type = %(etype)s")
        params["etype"] = entry_type

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    async with await get_connection() as conn:
        rows = await (
            await conn.execute(
                f"""
                SELECT id, spine_object_id, entry_type, content, source, created_at,
                       1 - (embedding <=> %(emb)s::vector) AS similarity
                FROM spine_agent.context_entries
                {where}
                ORDER BY embedding <=> %(emb)s::vector
                LIMIT %(lim)s
                """,
                params,
            )
        ).fetchall()
    return rows


async def search_structured(
    spine_object_id: str | None = None,
    entry_type: str | None = None,
    source: str | None = None,
    limit: int = 20,
    since: datetime | None = None,
) -> list[dict]:
    """Structured query by exact filters, ordered by created_at DESC."""
    where_parts: list[str] = []
    params: dict = {"lim": limit}

    if spine_object_id is not None:
        where_parts.append("spine_object_id = %(sid)s")
        params["sid"] = spine_object_id
    if entry_type is not None:
        where_parts.append("entry_type = %(etype)s")
        params["etype"] = entry_type
    if source is not None:
        where_parts.append("source = %(source)s")
        params["source"] = source
    if since is not None:
        where_parts.append("created_at >= %(since)s")
        params["since"] = since

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    async with await get_connection() as conn:
        rows = await (
            await conn.execute(
                f"""
                SELECT id, spine_object_id, entry_type, content, source, created_at
                FROM spine_agent.context_entries
                {where}
                ORDER BY created_at DESC
                LIMIT %(lim)s
                """,
                params,
            )
        ).fetchall()
    return rows


async def get_entries_for_spine(spine_object_id: str) -> list[dict]:
    """Convenience: all entries for a spine object, newest first."""
    return await search_structured(spine_object_id=spine_object_id)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _content_to_text(content: dict) -> str:
    """Convert JSONB content to a string suitable for embedding."""
    parts = []
    for key, value in content.items():
        parts.append(f"{key}: {value}")
    return " | ".join(parts)
