"""Skill Registry — backed by the spine_agent.skills table."""

from __future__ import annotations

import json

from agent.db import get_connection
from agent.embeddings import get_embedding
from skills.base_skill import BaseSkill


class SkillRegistry:
    """In-memory cache + DB persistence for agent skills."""

    def __init__(self) -> None:
        self._local: dict[str, BaseSkill] = {}

    # ── Registration ─────────────────────────────────────────────────────

    async def register(self, skill: BaseSkill) -> None:
        """Register a skill: cache locally and upsert into the DB."""
        self._local[skill.name] = skill
        embedding = await get_embedding(f"{skill.name}: {skill.description}")

        async with await get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO spine_agent.skills
                    (name, description, domain, trigger_type, spec,
                     code_path, author, description_embedding)
                VALUES (%(name)s, %(desc)s, %(domain)s, 'on_demand',
                        %(spec)s, %(code)s, 'human', %(emb)s::vector)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    domain      = EXCLUDED.domain,
                    spec        = EXCLUDED.spec,
                    code_path   = EXCLUDED.code_path,
                    description_embedding = EXCLUDED.description_embedding,
                    updated_at  = now()
                """,
                {
                    "name": skill.name,
                    "desc": skill.description,
                    "domain": skill.domain,
                    "spec": json.dumps(skill.get_spec()),
                    "code": f"skills.builtin.{skill.name}",
                    "emb": str(embedding),
                },
            )

    async def ensure_builtin_skills(self) -> None:
        """Auto-register all builtin skills.  Call at startup."""
        from skills.builtin import get_all_builtin_skills

        for skill in get_all_builtin_skills():
            await self.register(skill)

    # ── Lookup ───────────────────────────────────────────────────────────

    async def get(self, name: str) -> BaseSkill | None:
        """Get a skill by exact name from the local cache."""
        return self._local.get(name)

    async def search_by_domain(self, domain: str) -> list[dict]:
        """Find all enabled skills in a domain."""
        async with await get_connection() as conn:
            return await (
                await conn.execute(
                    """
                    SELECT id, name, description, domain, trigger_type, spec
                    FROM spine_agent.skills
                    WHERE domain = %(d)s AND enabled = true
                    ORDER BY name
                    """,
                    {"d": domain},
                )
            ).fetchall()

    async def search_semantic(self, query: str, limit: int = 5) -> list[dict]:
        """Semantic search over skill descriptions."""
        emb = await get_embedding(query)
        async with await get_connection() as conn:
            return await (
                await conn.execute(
                    """
                    SELECT id, name, description, domain,
                           1 - (description_embedding <=> %(emb)s::vector) AS similarity
                    FROM spine_agent.skills
                    WHERE enabled = true
                    ORDER BY description_embedding <=> %(emb)s::vector
                    LIMIT %(lim)s
                    """,
                    {"emb": str(emb), "lim": limit},
                )
            ).fetchall()

    async def record_usage(self, skill_name: str) -> None:
        """Increment usage_count and touch last_used_at."""
        async with await get_connection() as conn:
            await conn.execute(
                """
                UPDATE spine_agent.skills
                SET usage_count = usage_count + 1, last_used_at = now()
                WHERE name = %(n)s
                """,
                {"n": skill_name},
            )

    async def list_all(self, enabled_only: bool = True) -> list[dict]:
        """List all registered skills."""
        where = "WHERE enabled = true" if enabled_only else ""
        async with await get_connection() as conn:
            return await (
                await conn.execute(
                    f"SELECT id, name, description, domain, trigger_type, usage_count "
                    f"FROM spine_agent.skills {where} ORDER BY name"
                )
            ).fetchall()
