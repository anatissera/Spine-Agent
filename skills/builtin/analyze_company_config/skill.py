"""Skill: Analyze database structure and produce a schema report."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from skills.base_skill import BaseSkill


class AnalyzeCompanyConfig(BaseSkill):
    name = "analyze_company_config"
    description = (
        "Introspect the database schema and produce a comprehensive report of all "
        "schemas, tables, columns, primary keys, foreign keys, constraints, and "
        "business domain groupings"
    )
    domain = "cross-domain"

    def get_spec(self) -> dict[str, Any]:
        return {
            "inputs": {
                "schemas": {
                    "type": "list",
                    "required": False,
                    "description": "Schemas to include (default: all non-system)",
                },
                "exclude_schemas": {
                    "type": "list",
                    "required": False,
                    "description": "Schemas to exclude",
                },
                "include_row_counts": {
                    "type": "boolean",
                    "required": False,
                    "default": True,
                    "description": "Include approximate row counts from pg_stat_user_tables",
                },
            },
            "outputs": [
                "markdown_report",
                "schema_count",
                "table_count",
                "fk_count",
                "domains_detected",
                "schemas",
                "report_data",
            ],
            "dependencies": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        from agent.db import get_connection
        from skills.builtin.analyze_company_config.introspection import (
            assemble_report_data,
            detect_domains,
            generate_markdown,
            run_introspection,
        )

        exclude_schemas: set[str] = set(kwargs.get("exclude_schemas") or [])
        filter_schemas: set[str] | None = (
            set(kwargs["schemas"]) if kwargs.get("schemas") else None
        )
        include_row_counts: bool = kwargs.get("include_row_counts", True)

        t0 = time.monotonic()
        generated_at = datetime.now(timezone.utc).isoformat()

        async with await get_connection() as conn:
            introspection = await run_introspection(
                conn,
                excluded_schemas=exclude_schemas,
                include_row_counts=include_row_counts,
            )

        # Apply schema filter post-introspection
        if filter_schemas:
            introspection["tables"] = {
                s: t for s, t in introspection["tables"].items()
                if s in filter_schemas
            }
            introspection["schema_count"] = len(introspection["tables"])
            introspection["table_count"] = sum(
                len(t) for t in introspection["tables"].values()
            )
            allowed_keys = {
                f"{s}.{t}"
                for s, tbls in introspection["tables"].items()
                for t in tbls
            }
            introspection["columns"] = {
                k: v for k, v in introspection["columns"].items()
                if k in allowed_keys
            }
            introspection["primary_keys"] = {
                k: v for k, v in introspection["primary_keys"].items()
                if k in allowed_keys
            }
            introspection["foreign_keys"] = [
                fk for fk in introspection["foreign_keys"]
                if f"{fk['table_schema']}.{fk['table_name']}" in allowed_keys
            ]
            introspection["fk_count"] = len(introspection["foreign_keys"])
            introspection["unique_constraints"] = {
                k: v for k, v in introspection["unique_constraints"].items()
                if k in allowed_keys
            }
            introspection["check_constraints"] = {
                k: v for k, v in introspection["check_constraints"].items()
                if k in allowed_keys
            }

        detected_domains = detect_domains(introspection["tables"])
        report_data = assemble_report_data(introspection, detected_domains, generated_at)

        duration_ms = int((time.monotonic() - t0) * 1000)
        markdown = generate_markdown(report_data, "live", duration_ms)

        return {
            "success": True,
            "markdown_report": markdown,
            "schema_count": report_data["schema_count"],
            "table_count": report_data["table_count"],
            "fk_count": report_data["fk_count"],
            "domains_detected": report_data["domains_detected"],
            "schemas": report_data["schemas"],
            "report_data": report_data,
            "duration_ms": duration_ms,
        }
