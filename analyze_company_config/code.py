#!/usr/bin/env python3
"""
skills/builtin/analyze_company_config/code.py

Database Structure Report skill for SpineAgent.

Connects to a PostgreSQL database and introspects the full schema via
information_schema. Produces a comprehensive Markdown report containing:
  - All user schemas and tables with approximate row counts
  - All columns with data types, nullability, defaults, ordinal position
  - Primary key declarations per table
  - Foreign key relationships with ON DELETE / ON UPDATE rules
  - Unique constraints (including multi-column)
  - Check constraints (non-NULL only)
  - Business domain groupings and cross-domain FK analysis
  - AI verification checklist for all FK constraints

The report is structured so another AI agent can:
  1. Verify all FK relationships exist and are consistent
  2. Understand column-level semantics across the schema
  3. Navigate business domain boundaries without running SQL

Two output files are written to output_dir:
  - db_structure_latest.md           (always overwritten — canonical current state)
  - db_structure_YYYYMMDD_HHMMSS.md  (timestamped archive)

Cache-aside: if spine_agent.company_config_snapshots has a fresh snapshot within
cache_ttl_hours, returns it immediately without re-querying the live database.
Falls through gracefully if the cache table does not yet exist.

Usage:
    python skills/builtin/analyze_company_config/code.py
    python skills/builtin/analyze_company_config/code.py --dry-run
    python skills/builtin/analyze_company_config/code.py --force
    python skills/builtin/analyze_company_config/code.py --schemas sales production
    python skills/builtin/analyze_company_config/code.py --exclude-schemas spine_agent
    python skills/builtin/analyze_company_config/code.py --output-dir /tmp/reports

Requires:
    DATABASE_URL env var (PostgreSQL connection string)
    pip install psycopg2-binary
"""

import glob
import json
import logging
import os
import pathlib
import sys
import time
import traceback
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("analyze_company_config")

SKILL_VERSION = "1.0.0"
# Default output dir: three levels up from this file → project root / reports
DEFAULT_OUTPUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "reports")
)
LATEST_REPORT_FILENAME = "db_structure_latest.md"
DEFAULT_CACHE_TTL_HOURS = 6
DEFAULT_MAX_REPORT_FILES = 7
DEFAULT_KEEP_SNAPSHOTS_DAYS = 30
SYSTEM_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast"}

# Domain detection — mirrors DOMAIN_INDICATORS in company_config_collector.py.
# Copied intentionally: the skill must be independently runnable without
# importing from collectors/, which would create a fragile cross-directory dep.
DOMAIN_INDICATORS: dict[str, list[tuple[str, str]]] = {
    "sales":      [("sales", "salesorderheader"), ("sales", "customer")],
    "hr":         [("humanresources", "employee"), ("humanresources", "department")],
    "production": [("production", "product"), ("production", "workorder")],
    "purchasing": [("purchasing", "vendor"), ("purchasing", "purchaseorderheader")],
    "person":     [("person", "person"), ("person", "address")],
    "geography":  [("sales", "salesterritory"), ("person", "stateprovince")],
    "finance":    [("sales", "currencyrate"), ("sales", "salestaxrate")],
}

DOMAIN_PURPOSES: dict[str, str] = {
    "sales":      "Order management, customer relationships, pricing, and revenue tracking",
    "hr":         "Employee records, departments, payroll, and organizational structure",
    "production": "Product catalog, bill of materials, manufacturing, and inventory",
    "purchasing": "Vendor management, purchase orders, and supply chain",
    "person":     "Core entity registry — persons, addresses, and contact information",
    "geography":  "Sales territories, state/province hierarchy, and country references",
    "finance":    "Currency rates, tax rates, and financial reference data",
}


# ── SQL constants ──────────────────────────────────────────────────────────────────

# NOTE: {ph} is a placeholder for the NOT IN (...) list, filled by _placeholders().
# The actual schema names are passed as query parameters, never interpolated.

_SQL_TABLES_STATS = """
    SELECT
        schemaname  AS table_schema,
        tablename   AS table_name,
        n_live_tup  AS approx_rows
    FROM pg_stat_user_tables
    ORDER BY schemaname, tablename;
"""

_SQL_TABLES_FALLBACK = """
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema NOT IN ({ph})
      AND table_type = 'BASE TABLE'
    ORDER BY table_schema, table_name;
"""

_SQL_COLUMNS = """
    SELECT
        table_schema,
        table_name,
        column_name,
        ordinal_position,
        column_default,
        is_nullable,
        data_type,
        character_maximum_length,
        numeric_precision,
        numeric_scale
    FROM information_schema.columns
    WHERE table_schema NOT IN ({ph})
    ORDER BY table_schema, table_name, ordinal_position;
"""

_SQL_PRIMARY_KEYS = """
    SELECT
        kcu.table_schema,
        kcu.table_name,
        kcu.column_name,
        kcu.ordinal_position
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema    = kcu.table_schema
     AND tc.table_name      = kcu.table_name
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_schema NOT IN ({ph})
    ORDER BY kcu.table_schema, kcu.table_name, kcu.ordinal_position;
"""

# Cross-schema safe FK query: uses rc.unique_constraint_name/schema to join ccu,
# so the referenced table's schema can differ from the source schema.
_SQL_FOREIGN_KEYS = """
    SELECT
        tc.constraint_name,
        tc.table_schema,
        tc.table_name,
        kcu.column_name,
        ccu.table_schema  AS foreign_table_schema,
        ccu.table_name    AS foreign_table_name,
        ccu.column_name   AS foreign_column_name,
        rc.delete_rule,
        rc.update_rule
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema    = kcu.table_schema
     AND tc.table_name      = kcu.table_name
    JOIN information_schema.referential_constraints rc
      ON rc.constraint_name   = tc.constraint_name
     AND rc.constraint_schema = tc.table_schema
    JOIN information_schema.key_column_usage ccu
      ON ccu.constraint_name = rc.unique_constraint_name
     AND ccu.table_schema    = rc.unique_constraint_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema NOT IN ({ph})
    ORDER BY tc.table_schema, tc.table_name, kcu.column_name;
"""

_SQL_UNIQUE_CONSTRAINTS = """
    SELECT
        tc.table_schema,
        tc.table_name,
        tc.constraint_name,
        kcu.column_name,
        kcu.ordinal_position
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema    = kcu.table_schema
     AND tc.table_name      = kcu.table_name
    WHERE tc.constraint_type = 'UNIQUE'
      AND tc.table_schema NOT IN ({ph})
    ORDER BY tc.table_schema, tc.table_name, tc.constraint_name, kcu.ordinal_position;
"""

_SQL_CHECK_CONSTRAINTS = """
    SELECT
        tc.table_schema,
        tc.table_name,
        tc.constraint_name,
        cc.check_clause
    FROM information_schema.table_constraints tc
    JOIN information_schema.check_constraints cc
      ON cc.constraint_name   = tc.constraint_name
     AND cc.constraint_schema = tc.table_schema
    WHERE tc.constraint_type = 'CHECK'
      AND tc.table_schema NOT IN ({ph})
      AND cc.check_clause NOT LIKE '%%IS NOT NULL%%'
    ORDER BY tc.table_schema, tc.table_name, tc.constraint_name;
"""


# ── Helpers ───────────────────────────────────────────────────────────────────────

def _placeholders(excluded: set[str]) -> tuple[str, list[str]]:
    """
    Build (placeholder_string, params_list) for a NOT IN (...) clause.
    Always includes SYSTEM_SCHEMAS in the exclusion set.
    Parameters are never interpolated — only %s placeholders are generated.
    """
    all_exc = SYSTEM_SCHEMAS | excluded
    params = sorted(all_exc)   # sorted for deterministic query plans
    ph = ", ".join(["%s"] * len(params))
    return ph, params


def _fmt_ph(sql_template: str, excluded: set[str]) -> tuple[str, list[str]]:
    """Fill {ph} in a SQL template and return (sql, params)."""
    ph, params = _placeholders(excluded)
    return sql_template.format(ph=ph), params


# ── Schema introspection ─────────────────────────────────────────────────────────

def introspect_tables(
    cur, excluded_schemas: set[str], include_row_counts: bool = True
) -> dict[str, dict[str, int | None]]:
    """
    Returns {schema: {table: approx_row_count_or_None}}.
    Uses pg_stat_user_tables for row counts when include_row_counts=True,
    falling back to information_schema.tables (no counts) on error.
    """
    tables: dict[str, dict[str, int | None]] = {}

    if include_row_counts:
        try:
            cur.execute(_SQL_TABLES_STATS)
            for row in cur.fetchall():
                s, t = row["table_schema"], row["table_name"]
                if s not in excluded_schemas and s not in SYSTEM_SCHEMAS:
                    tables.setdefault(s, {})[t] = row["approx_rows"]
            return tables
        except Exception as e:
            log.warning(f"pg_stat_user_tables unavailable ({e}), falling back to information_schema")

    sql, params = _fmt_ph(_SQL_TABLES_FALLBACK, excluded_schemas)
    cur.execute(sql, params)
    for row in cur.fetchall():
        tables.setdefault(row["table_schema"], {})[row["table_name"]] = None
    return tables


def introspect_columns(
    cur, excluded_schemas: set[str]
) -> dict[str, list[dict]]:
    """
    Returns {"schema.table": [col_dict, ...]} in ordinal order.
    Each col_dict: column_name, ordinal_position, column_default, is_nullable,
                   data_type, character_maximum_length, numeric_precision, numeric_scale.
    """
    sql, params = _fmt_ph(_SQL_COLUMNS, excluded_schemas)
    cur.execute(sql, params)
    result: dict[str, list[dict]] = {}
    for row in cur.fetchall():
        key = f"{row['table_schema']}.{row['table_name']}"
        result.setdefault(key, []).append(dict(row))
    return result


def introspect_primary_keys(
    cur, excluded_schemas: set[str]
) -> dict[str, list[str]]:
    """Returns {"schema.table": [pk_col, ...]} in ordinal order."""
    sql, params = _fmt_ph(_SQL_PRIMARY_KEYS, excluded_schemas)
    cur.execute(sql, params)
    result: dict[str, list[str]] = {}
    for row in cur.fetchall():
        key = f"{row['table_schema']}.{row['table_name']}"
        result.setdefault(key, []).append(row["column_name"])
    return result


def introspect_foreign_keys(
    cur, excluded_schemas: set[str]
) -> list[dict]:
    """
    Returns a flat list of FK dicts. Each dict has:
        constraint_name, table_schema, table_name, column_name,
        foreign_table_schema, foreign_table_name, foreign_column_name,
        delete_rule, update_rule
    Cross-schema FKs are correctly captured via the referential_constraints join.
    """
    sql, params = _fmt_ph(_SQL_FOREIGN_KEYS, excluded_schemas)
    cur.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


def introspect_unique_constraints(
    cur, excluded_schemas: set[str]
) -> dict[str, list[dict]]:
    """
    Returns {"schema.table": [{"constraint_name": str, "columns": [str,...]}, ...]}.
    Multi-column unique constraints are collapsed into a single entry.
    """
    sql, params = _fmt_ph(_SQL_UNIQUE_CONSTRAINTS, excluded_schemas)
    cur.execute(sql, params)

    # Group columns by (schema.table, constraint_name)
    raw: dict[str, dict[str, list[str]]] = {}
    for row in cur.fetchall():
        key = f"{row['table_schema']}.{row['table_name']}"
        raw.setdefault(key, {}).setdefault(row["constraint_name"], []).append(
            row["column_name"]
        )

    result: dict[str, list[dict]] = {}
    for table_key, constraints in raw.items():
        result[table_key] = [
            {"constraint_name": cname, "columns": cols}
            for cname, cols in constraints.items()
        ]
    return result


def introspect_check_constraints(
    cur, excluded_schemas: set[str]
) -> dict[str, list[dict]]:
    """
    Returns {"schema.table": [{"constraint_name": str, "check_clause": str}, ...]}.
    Automatically-generated NOT NULL checks are excluded.
    """
    sql, params = _fmt_ph(_SQL_CHECK_CONSTRAINTS, excluded_schemas)
    cur.execute(sql, params)
    result: dict[str, list[dict]] = {}
    for row in cur.fetchall():
        key = f"{row['table_schema']}.{row['table_name']}"
        result.setdefault(key, []).append({
            "constraint_name": row["constraint_name"],
            "check_clause": row["check_clause"],
        })
    return result


def run_introspection(
    cur,
    excluded_schemas: set[str],
    include_row_counts: bool = True,
) -> dict[str, Any]:
    """
    Runs all introspection functions. Each is wrapped in try/except — failures
    append to errors and the function continues with partial results.

    Returns a dict with keys:
        tables, columns, primary_keys, foreign_keys, unique_constraints,
        check_constraints, errors, schema_count, table_count, fk_count
    """
    errors: list[str] = []
    tables: dict = {}
    columns: dict = {}
    primary_keys: dict = {}
    foreign_keys: list = []
    unique_constraints: dict = {}
    check_constraints: dict = {}

    try:
        tables = introspect_tables(cur, excluded_schemas, include_row_counts)
    except Exception as e:
        errors.append(f"tables: {e}")
        log.error(f"introspect_tables failed: {e}")

    try:
        columns = introspect_columns(cur, excluded_schemas)
    except Exception as e:
        errors.append(f"columns: {e}")
        log.error(f"introspect_columns failed: {e}")

    try:
        primary_keys = introspect_primary_keys(cur, excluded_schemas)
    except Exception as e:
        errors.append(f"primary_keys: {e}")
        log.error(f"introspect_primary_keys failed: {e}")

    try:
        foreign_keys = introspect_foreign_keys(cur, excluded_schemas)
    except Exception as e:
        errors.append(f"foreign_keys: {e}")
        log.error(f"introspect_foreign_keys failed: {e}")

    try:
        unique_constraints = introspect_unique_constraints(cur, excluded_schemas)
    except Exception as e:
        errors.append(f"unique_constraints: {e}")
        log.error(f"introspect_unique_constraints failed: {e}")

    try:
        check_constraints = introspect_check_constraints(cur, excluded_schemas)
    except Exception as e:
        errors.append(f"check_constraints: {e}")
        log.error(f"introspect_check_constraints failed: {e}")

    schema_count = len(tables)
    table_count = sum(len(t) for t in tables.values())
    fk_count = len(foreign_keys)

    return {
        "tables": tables,
        "columns": columns,
        "primary_keys": primary_keys,
        "foreign_keys": foreign_keys,
        "unique_constraints": unique_constraints,
        "check_constraints": check_constraints,
        "errors": errors,
        "schema_count": schema_count,
        "table_count": table_count,
        "fk_count": fk_count,
    }


# ── Domain detection ──────────────────────────────────────────────────────────────

def table_exists(tables: dict[str, dict], schema: str, table: str) -> bool:
    """True if schema.table is present in the introspected tables dict."""
    return table in tables.get(schema, {})


def detect_domains(tables: dict[str, dict]) -> list[str]:
    """
    Returns list of detected business domains from DOMAIN_INDICATORS.
    A domain is included if at least one indicator table exists.
    """
    return [
        domain
        for domain, indicators in DOMAIN_INDICATORS.items()
        if any(table_exists(tables, s, t) for s, t in indicators)
    ]


# ── Report data assembly ──────────────────────────────────────────────────────────

def build_fk_index(foreign_keys: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """
    Builds two lookup indexes over the FK list:
      result["from"]["schema.table"] → [fk_dict, ...]   FKs originating here
      result["to"]["schema.table"]   → [fk_dict, ...]   FKs pointing here
    """
    from_idx: dict[str, list[dict]] = defaultdict(list)
    to_idx: dict[str, list[dict]] = defaultdict(list)

    for fk in foreign_keys:
        src_key = f"{fk['table_schema']}.{fk['table_name']}"
        dst_key = f"{fk['foreign_table_schema']}.{fk['foreign_table_name']}"
        from_idx[src_key].append(fk)
        to_idx[dst_key].append(fk)

    return {"from": dict(from_idx), "to": dict(to_idx)}


def describe_column_type(col: dict) -> str:
    """
    Produces a compact human-readable type string from a column metadata dict.
    Examples:
        character varying, max_len=50  → varchar(50)
        numeric, prec=19, scale=4      → numeric(19,4)
        integer                        → integer
        ARRAY                          → array
        USER-DEFINED                   → user-defined
    """
    dt = (col.get("data_type") or "").lower()
    if dt in ("character varying", "varchar"):
        ml = col.get("character_maximum_length")
        return f"varchar({ml})" if ml else "varchar"
    if dt == "character":
        ml = col.get("character_maximum_length")
        return f"char({ml})" if ml else "char"
    if dt == "numeric" or dt == "decimal":
        p, s = col.get("numeric_precision"), col.get("numeric_scale")
        if p is not None and s is not None:
            return f"{dt}({p},{s})"
        if p is not None:
            return f"{dt}({p})"
        return dt
    if dt == "array":
        return "array"
    if dt == "user-defined":
        return "user-defined"
    return dt or "unknown"


def build_domain_architecture(
    detected_domains: list[str],
    tables: dict[str, dict],
    fk_index: dict[str, dict[str, list[dict]]],
) -> dict[str, dict]:
    """
    For each detected domain, produces:
      schemas: schemas that contain the domain's indicator tables
      core_tables: indicator tables that exist
      business_purpose: hardcoded human description
      internal_fks: count of FKs where both endpoints belong to domain schemas
      cross_domain_fks: list of {from, to, column} for FKs crossing domain boundaries
    """
    # Map domain → set of schemas
    domain_schemas: dict[str, set[str]] = {}
    for domain, indicators in DOMAIN_INDICATORS.items():
        if domain not in detected_domains:
            continue
        domain_schemas[domain] = {s for s, t in indicators if table_exists(tables, s, t)}

    result: dict[str, dict] = {}
    for domain in detected_domains:
        my_schemas = domain_schemas.get(domain, set())
        core_tables = [
            f"{s}.{t}"
            for s, t in DOMAIN_INDICATORS[domain]
            if table_exists(tables, s, t)
        ]

        internal_fks = 0
        cross_domain: list[dict] = []

        for fk in fk_index.get("from", {}).values():
            for fk_entry in fk:
                src_schema = fk_entry["table_schema"]
                dst_schema = fk_entry["foreign_table_schema"]
                if src_schema in my_schemas:
                    if dst_schema in my_schemas:
                        internal_fks += 1
                    else:
                        # Find which domain owns the destination
                        dst_domain = next(
                            (d for d, s in domain_schemas.items() if dst_schema in s),
                            "unknown",
                        )
                        cross_domain.append({
                            "from": f"{src_schema}.{fk_entry['table_name']}({fk_entry['column_name']})",
                            "to": f"{dst_schema}.{fk_entry['foreign_table_name']}({fk_entry['foreign_column_name']})",
                            "to_domain": dst_domain,
                        })

        result[domain] = {
            "schemas": sorted(my_schemas),
            "core_tables": core_tables,
            "business_purpose": DOMAIN_PURPOSES.get(domain, ""),
            "internal_fks": internal_fks,
            "cross_domain_fks": cross_domain,
        }

    return result


def assemble_report_data(
    introspection: dict,
    detected_domains: list[str],
    generated_at: str,
) -> dict[str, Any]:
    """
    Combines all introspection results into a single structured dict used
    both as the JSONB payload for the cache table and for Markdown rendering.
    """
    fk_index = build_fk_index(introspection["foreign_keys"])
    domain_arch = build_domain_architecture(
        detected_domains, introspection["tables"], fk_index
    )

    return {
        "generated_at": generated_at,
        "skill_version": SKILL_VERSION,
        "schema_count": introspection["schema_count"],
        "table_count": introspection["table_count"],
        "fk_count": introspection["fk_count"],
        "schemas": sorted(introspection["tables"].keys()),
        "tables": introspection["tables"],
        "columns": introspection["columns"],
        "primary_keys": introspection["primary_keys"],
        "foreign_keys": introspection["foreign_keys"],
        "unique_constraints": introspection["unique_constraints"],
        "check_constraints": introspection["check_constraints"],
        "domains_detected": detected_domains,
        "domain_architecture": domain_arch,
        "fk_index": fk_index,
        "errors": introspection["errors"],
    }


# ── Markdown rendering ────────────────────────────────────────────────────────────

def _md_table(headers: list[str], rows: list[list]) -> str:
    """Render a Markdown pipe table. None values become empty strings."""
    def _cell(v: Any) -> str:
        return str(v).replace("|", "\\|") if v is not None else ""

    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = [
        "|" + "|".join(headers) + "|",
        sep,
    ]
    for row in rows:
        lines.append("|" + "|".join(_cell(c) for c in row) + "|")
    return "\n".join(lines)


def _fmt_nullable(v: str) -> str:
    return "Y" if v == "YES" else "N"


def _find_hub_table(fk_index: dict) -> str | None:
    """Returns the table with the most inbound FK references."""
    to_idx = fk_index.get("to", {})
    if not to_idx:
        return None
    return max(to_idx, key=lambda k: len(to_idx[k]))


def generate_markdown(report_data: dict, source: str, duration_ms: int) -> str:
    """
    Renders the full database structure report as a Markdown string.
    Sections (in order):
      1. Header block
      2. Executive Summary
      3. Domain Overview table
      4. Per-schema sections (tables + columns + FKs + constraints)
      5. Full Relationship Map
      6. Domain-Grouped Architecture
      7. AI Verification Checklist
    """
    lines: list[str] = []

    tables = report_data["tables"]
    columns = report_data["columns"]
    primary_keys = report_data["primary_keys"]
    foreign_keys = report_data["foreign_keys"]
    unique_constraints = report_data["unique_constraints"]
    check_constraints = report_data["check_constraints"]
    domains = report_data["domains_detected"]
    domain_arch = report_data["domain_architecture"]
    fk_index = report_data["fk_index"]
    schemas = report_data["schemas"]
    schema_count = report_data["schema_count"]
    table_count = report_data["table_count"]
    fk_count = report_data["fk_count"]
    generated_at = report_data["generated_at"]

    # ── 1. Header ──
    lines += [
        "# Company Database Structure Report",
        "",
        f"Generated: {generated_at}  "
        f"| Source: {source}  "
        f"| Duration: {duration_ms}ms  "
        f"| Skill version: {SKILL_VERSION}",
        "",
        f"**Schemas:** {schema_count}  "
        f"| **Tables:** {table_count}  "
        f"| **Foreign Keys:** {fk_count}  "
        f"| **Domains:** {len(domains)}",
        "",
    ]

    # ── 2. Executive Summary ──
    hub = _find_hub_table(fk_index)
    hub_inbound = len(fk_index["to"].get(hub, [])) if hub else 0
    domain_list = ", ".join(domains) if domains else "none detected"
    lines += [
        "## Executive Summary",
        "",
        f"This database contains **{schema_count} schemas** and **{table_count} tables** "
        f"spanning **{len(domains)} business domains**: {domain_list}. "
        f"The schema is connected by **{fk_count} foreign key relationships**.",
    ]
    if hub:
        lines.append(
            f" The central entity hub is **{hub}**, which is referenced by "
            f"{hub_inbound} inbound FK constraints."
        )
    lines.append("")

    # ── 3. Domain Overview ──
    if domains:
        lines += ["## Domain Overview", ""]
        dom_rows = []
        for d in domains:
            arch = domain_arch.get(d, {})
            core = ", ".join(arch.get("core_tables", [])[:3])
            schemas_in_domain = ", ".join(arch.get("schemas", []))
            dom_rows.append([d, schemas_in_domain, core, arch.get("business_purpose", "")])
        lines.append(_md_table(["Domain", "Schemas", "Core Tables", "Business Purpose"], dom_rows))
        lines.append("")

    # ── 4. Per-schema sections ──
    for schema in schemas:
        schema_tables = tables.get(schema, {})
        inbound_to_schema = sum(
            len(fk_index["to"].get(f"{schema}.{t}", []))
            for t in schema_tables
        )
        lines += [
            f"## Schema: {schema}",
            "",
            f"{len(schema_tables)} tables | {inbound_to_schema} inbound FK references from other schemas",
            "",
        ]

        for table_name in sorted(schema_tables.keys()):
            key = f"{schema}.{table_name}"
            row_count = schema_tables[table_name]
            row_str = f"~{row_count:,}" if row_count is not None else "unknown"
            pk_cols = set(primary_keys.get(key, []))
            fk_from_here = {fk["column_name"]: fk for fk in fk_index["from"].get(key, [])}

            lines += [
                f"### Table: {key}  ({row_str} rows)",
                "",
            ]

            # Column table
            col_rows = []
            for col in columns.get(key, []):
                cname = col["column_name"]
                ctype = describe_column_type(col)
                nullable = _fmt_nullable(col.get("is_nullable", "YES"))
                default = col.get("column_default") or ""
                if len(default) > 40:
                    default = default[:37] + "..."
                pk_marker = "PK" if cname in pk_cols else ""
                fk_ref = ""
                if cname in fk_from_here:
                    fk = fk_from_here[cname]
                    fk_ref = f"→ {fk['foreign_table_schema']}.{fk['foreign_table_name']}({fk['foreign_column_name']})"
                col_rows.append([cname, ctype, nullable, default, pk_marker, fk_ref])

            if col_rows:
                lines.append(_md_table(
                    ["Column", "Type", "Nullable", "Default", "PK", "FK Reference"],
                    col_rows,
                ))
                lines.append("")

            # FKs FROM this table (outbound)
            outbound = fk_index["from"].get(key, [])
            if outbound:
                lines.append("**Foreign Keys FROM this table:**")
                lines.append("")
                for fk in outbound:
                    rule = f" [ON DELETE {fk['delete_rule']}]" if fk.get("delete_rule") and fk["delete_rule"] != "NO ACTION" else ""
                    lines.append(
                        f"- `{fk['column_name']}` → "
                        f"`{fk['foreign_table_schema']}.{fk['foreign_table_name']}"
                        f"({fk['foreign_column_name']})`{rule}"
                        f"  _{fk['constraint_name']}_"
                    )
                lines.append("")

            # FKs TO this table (inbound)
            inbound = fk_index["to"].get(key, [])
            if inbound:
                lines.append("**Foreign Keys TO this table (inbound references):**")
                lines.append("")
                for fk in inbound:
                    lines.append(
                        f"- `{fk['table_schema']}.{fk['table_name']}"
                        f"({fk['column_name']})` → `{fk['foreign_column_name']}`"
                    )
                lines.append("")

            # Unique constraints
            ucs = unique_constraints.get(key, [])
            if ucs:
                lines.append("**Unique Constraints:**")
                lines.append("")
                for uc in ucs:
                    cols_str = ", ".join(uc["columns"])
                    lines.append(f"- `{uc['constraint_name']}`: ({cols_str})")
                lines.append("")

            # Check constraints
            ccs = check_constraints.get(key, [])
            if ccs:
                lines.append("**Check Constraints:**")
                lines.append("")
                for cc in ccs:
                    lines.append(f"- `{cc['constraint_name']}`: {cc['check_clause']}")
                lines.append("")

    # ── 5. Full Relationship Map ──
    lines += [
        f"## Relationship Map",
        "",
        f"### All Foreign Keys ({fk_count} total)",
        "",
    ]
    if foreign_keys:
        fk_rows = [
            [
                fk["table_schema"],
                fk["table_name"],
                fk["column_name"],
                fk["foreign_table_schema"],
                fk["foreign_table_name"],
                fk["foreign_column_name"],
                fk.get("delete_rule", ""),
                fk.get("update_rule", ""),
            ]
            for fk in foreign_keys
        ]
        lines.append(_md_table(
            ["From Schema", "From Table", "From Column",
             "To Schema", "To Table", "To Column",
             "On Delete", "On Update"],
            fk_rows,
        ))
    else:
        lines.append("_No foreign key constraints found._")
    lines.append("")

    # ── 6. Domain-Grouped Architecture ──
    if domains:
        lines += ["## Domain-Grouped Architecture", ""]
        for d in domains:
            arch = domain_arch.get(d, {})
            lines += [
                f"### Domain: {d}",
                "",
                f"**Business Purpose:** {arch.get('business_purpose', '')}  ",
                f"**Schemas:** {', '.join(arch.get('schemas', []))}",
                "",
                f"**Tables ({len(arch.get('core_tables', []))}):** "
                + ", ".join(arch.get("core_tables", [])),
                "",
            ]
            cross = arch.get("cross_domain_fks", [])
            if cross:
                lines.append("**Cross-domain FK connections:**")
                lines.append("")
                for c in cross:
                    lines.append(f"- `{c['from']}` → `{c['to']}` (domain: {c['to_domain']})")
                lines.append("")
            else:
                lines.append("_No outbound cross-domain FK connections._")
                lines.append("")

    # ── 7. AI Verification Checklist ──
    lines += [
        "## AI Verification Checklist",
        "",
        "This section lists all structural invariants an AI agent should verify",
        "before marking this schema as consistent.",
        "",
    ]

    if foreign_keys:
        lines += [f"### Foreign Key Verification ({fk_count} constraints)", ""]
        for fk in foreign_keys:
            lines.append(
                f"- [ ] `{fk['table_schema']}.{fk['table_name']}"
                f"({fk['column_name']})` → "
                f"`{fk['foreign_table_schema']}.{fk['foreign_table_name']}"
                f"({fk['foreign_column_name']})` "
                f"— constraint: `{fk['constraint_name']}`"
            )
        lines.append("")

    lines += ["### Schema Completeness Verification", ""]
    for schema in schemas:
        n = len(tables.get(schema, {}))
        lines.append(f"- [ ] Schema `{schema}` contains {n} table{'s' if n != 1 else ''}")
    lines.append("")

    if hub:
        lines += [
            "### Hub Table Integrity",
            "",
            f"- [ ] `{hub}` is referenced by at least {hub_inbound} inbound FK constraints",
            "",
        ]

    if report_data.get("errors"):
        lines += [
            "### Introspection Errors",
            "",
            "_The following non-fatal errors occurred during introspection:_",
            "",
        ]
        for err in report_data["errors"]:
            lines.append(f"- {err}")
        lines.append("")

    return "\n".join(lines)


# ── File output ───────────────────────────────────────────────────────────────────

def write_report_files(
    markdown: str,
    output_dir: str,
    max_files: int = DEFAULT_MAX_REPORT_FILES,
    dry_run: bool = False,
) -> tuple[str | None, str | None]:
    """
    Writes db_structure_latest.md and a timestamped archive copy.
    Prunes archive files beyond max_files (oldest first).
    Returns (latest_path, archive_path). Both None on dry_run.
    """
    if dry_run:
        log.info("[DRY RUN] Would write .md files — skipping.")
        return None, None

    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    latest = out / LATEST_REPORT_FILENAME
    latest.write_text(markdown, encoding="utf-8")
    log.info(f"Report written  → {latest}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out / f"db_structure_{ts}.md"
    archive.write_text(markdown, encoding="utf-8")
    log.info(f"Archive written → {archive}")

    pattern = str(out / "db_structure_2*.md")
    existing = sorted(glob.glob(pattern))
    for old in existing[:-max_files]:
        pathlib.Path(old).unlink(missing_ok=True)
        log.info(f"Pruned old archive: {old}")

    return str(latest), str(archive)


# ── Cache-aside ───────────────────────────────────────────────────────────────────

def read_cached_report(conn, cache_ttl_hours: int) -> dict | None:
    """
    Attempts to read a fresh snapshot from spine_agent.company_config_snapshots.
    Returns the row dict on cache hit, None on miss or any error (table missing, etc.).
    """
    if cache_ttl_hours <= 0:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, collected_at, domains_detected, report, markdown_summary, "
                "collection_duration_ms FROM spine_agent.latest_config_snapshot(%s) LIMIT 1;",
                (cache_ttl_hours,),
            )
            row = cur.fetchone()
            if row:
                age_min = (
                    datetime.now(timezone.utc) - row["collected_at"].replace(tzinfo=timezone.utc)
                ).total_seconds() / 60
                log.info(f"Cache hit — snapshot id={row['id']}, age={age_min:.1f}min")
                return dict(row)
    except Exception as e:
        log.info(f"Cache read skipped: {e}")
    return None


def write_cache_snapshot(
    conn,
    report_data: dict,
    markdown: str,
    detected_domains: list[str],
    duration_ms: int,
    errors: list[str],
    dry_run: bool = False,
) -> int | None:
    """
    Inserts into spine_agent.company_config_snapshots.
    raw_metrics = {} (this skill collects structure, not business metrics).
    confidence = 'high' (structural introspection is deterministic).
    Returns the new snapshot id, or None on dry_run / table-missing.
    """
    if dry_run:
        log.info("[DRY RUN] Would write DB snapshot — skipping.")
        return None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO spine_agent.company_config_snapshots
                    (collected_at, collector_version, domains_detected,
                     raw_metrics, report, markdown_summary, confidence,
                     collection_duration_ms, error_log)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    SKILL_VERSION,
                    detected_domains,
                    json.dumps({}),                  # raw_metrics — NOT NULL, empty here
                    json.dumps(report_data, default=str),
                    markdown,
                    "high",                          # confidence — always high for structural data
                    duration_ms,
                    json.dumps(errors),
                ),
            )
            snapshot_id = cur.fetchone()["id"]

            # Prune old snapshots
            cur.execute(
                "DELETE FROM spine_agent.company_config_snapshots "
                "WHERE collected_at < NOW() - INTERVAL '%s days';",
                (DEFAULT_KEEP_SNAPSHOTS_DAYS,),
            )
            conn.commit()
            log.info(f"Cache snapshot written — id={snapshot_id}")
            return snapshot_id
    except Exception as e:
        log.warning(f"Cache write skipped (table may not exist yet): {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None


# ── Entrypoint ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Database Structure Report — introspects PostgreSQL and generates Markdown"
    )
    parser.add_argument(
        "--output-dir", type=str, default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for .md files (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--schemas", nargs="*", default=[],
        metavar="SCHEMA",
        help="Schemas to include (default: all non-system schemas)"
    )
    parser.add_argument(
        "--exclude-schemas", nargs="*", default=[],
        metavar="SCHEMA",
        help="Schemas to exclude (in addition to system schemas)"
    )
    parser.add_argument(
        "--no-row-counts", action="store_true",
        help="Skip pg_stat_user_tables query"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run queries, print report to stdout, but write nothing"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Ignore cache — always run live introspection"
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable cache read/write entirely"
    )
    parser.add_argument(
        "--cache-ttl-hours", type=int, default=DEFAULT_CACHE_TTL_HOURS,
        help=f"Cache TTL in hours (0 = always live; default: {DEFAULT_CACHE_TTL_HOURS})"
    )
    parser.add_argument(
        "--max-report-files", type=int, default=DEFAULT_MAX_REPORT_FILES,
        help=f"Max archived .md files to keep (default: {DEFAULT_MAX_REPORT_FILES})"
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        log.error("DATABASE_URL environment variable is not set.")
        return 1

    try:
        conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        log.error(f"Failed to connect to database: {e}")
        return 1

    use_cache = not args.no_cache and not args.force
    cache_ttl = 0 if args.no_cache else args.cache_ttl_hours

    # ── Cache check ──
    if use_cache and cache_ttl > 0:
        cached = read_cached_report(conn, cache_ttl)
        if cached:
            if args.dry_run:
                print(cached.get("markdown_summary", ""))
            else:
                latest, _ = write_report_files(
                    cached["markdown_summary"],
                    args.output_dir,
                    args.max_report_files,
                    dry_run=False,
                )
                log.info(f"Served from cache → {latest}")
            conn.close()
            return 0

    # ── Live introspection ──
    excluded: set[str] = set(args.exclude_schemas)
    # If --schemas is given, exclude everything not in that list
    # by synthesising a block-all-then-allow pattern:
    # We let introspect_tables fetch all, then filter afterward — simpler
    # than rewriting all SQL. (The schemas arg is handled post-introspection.)
    filter_schemas: set[str] | None = set(args.schemas) if args.schemas else None

    t0 = time.monotonic()
    generated_at = datetime.now(timezone.utc).isoformat()

    with conn.cursor() as cur:
        introspection = run_introspection(
            cur,
            excluded_schemas=excluded,
            include_row_counts=not args.no_row_counts,
        )

    # Apply --schemas filter after introspection
    if filter_schemas:
        introspection["tables"] = {
            s: t for s, t in introspection["tables"].items()
            if s in filter_schemas
        }
        introspection["schema_count"] = len(introspection["tables"])
        introspection["table_count"] = sum(len(t) for t in introspection["tables"].values())
        allowed_keys = {
            f"{s}.{t}"
            for s, tables in introspection["tables"].items()
            for t in tables
        }
        introspection["columns"] = {k: v for k, v in introspection["columns"].items() if k in allowed_keys}
        introspection["primary_keys"] = {k: v for k, v in introspection["primary_keys"].items() if k in allowed_keys}
        introspection["foreign_keys"] = [
            fk for fk in introspection["foreign_keys"]
            if f"{fk['table_schema']}.{fk['table_name']}" in allowed_keys
        ]
        introspection["fk_count"] = len(introspection["foreign_keys"])
        introspection["unique_constraints"] = {k: v for k, v in introspection["unique_constraints"].items() if k in allowed_keys}
        introspection["check_constraints"] = {k: v for k, v in introspection["check_constraints"].items() if k in allowed_keys}

    detected_domains = detect_domains(introspection["tables"])
    report_data = assemble_report_data(introspection, detected_domains, generated_at)

    duration_ms = int((time.monotonic() - t0) * 1000)
    source = "live"
    markdown = generate_markdown(report_data, source, duration_ms)

    log.info(
        f"Introspection complete — schemas={report_data['schema_count']}, "
        f"tables={report_data['table_count']}, fks={report_data['fk_count']}, "
        f"domains={detected_domains}, duration={duration_ms}ms"
    )

    if args.dry_run:
        print(markdown)
        conn.close()
        return 0

    latest_path, archive_path = write_report_files(
        markdown, args.output_dir, args.max_report_files
    )

    if not args.no_cache:
        write_cache_snapshot(
            conn, report_data, markdown, detected_domains,
            duration_ms, introspection["errors"],
        )

    conn.close()

    log.info(f"Done. Report: {latest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
