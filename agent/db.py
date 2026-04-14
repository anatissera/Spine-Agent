"""Async database connection factory for SpineAgent."""

import psycopg
from pgvector.psycopg import register_vector_async

from agent.config import get_settings


async def get_connection() -> psycopg.AsyncConnection:
    """Create a new async connection with pgvector support.

    Usage::

        async with await get_connection() as conn:
            result = await conn.execute("SELECT 1")
    """
    settings = get_settings()
    conn = await psycopg.AsyncConnection.connect(
        settings.database_url,
        autocommit=True,
        row_factory=psycopg.rows.dict_row,
    )
    await register_vector_async(conn)
    return conn
