"""Embedding generation for SpineAgent context store and skill registry."""

from __future__ import annotations

import hashlib
import struct

import numpy as np

from agent.config import get_settings


async def get_embedding(text: str) -> list[float]:
    """Generate a 1536-dim embedding vector for *text*.

    Uses Voyage AI API if ``VOYAGE_API_KEY`` is set, otherwise falls back to a
    deterministic hash-based pseudo-embedding (not semantically meaningful, but
    stable and testable).
    """
    settings = get_settings()
    if settings.voyage_api_key:
        return await _voyage_embedding(text, settings)
    return _hash_embedding(text, settings.embedding_dimensions)


def _hash_embedding(text: str, dims: int = 1536) -> list[float]:
    """Deterministic pseudo-embedding derived from SHA-256.

    Identical inputs always produce the same vector.  Different inputs produce
    pseudo-random vectors with roughly orthogonal directions.  Useful for
    structured queries and testing without an API key.
    """
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "little")
    rng = np.random.Generator(np.random.PCG64(seed))
    vec = rng.standard_normal(dims).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec.tolist()


async def _voyage_embedding(text: str, settings) -> list[float]:
    """Call Voyage AI API for a real semantic embedding."""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={"model": "voyage-3-lite", "input": [text]},
        )
        resp.raise_for_status()
        raw = resp.json()["data"][0]["embedding"]

    # Pad or truncate to match the configured dimensions
    dims = settings.embedding_dimensions
    if len(raw) < dims:
        raw.extend([0.0] * (dims - len(raw)))
    return raw[:dims]
