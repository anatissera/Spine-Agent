"""Database introspection and Markdown report generation.

Extracted from analyze_company_config/code.py and converted to async psycopg3.
Queries information_schema to produce a comprehensive schema report including
tables, columns, PKs, FKs, constraints, row counts, and business domain groupings.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import psycopg

log = logging.getLogger("analyze_company_config")

SKILL_VERSION = "1.0.0"
SYSTEM_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast"}

# Domain detection — indicator tables whose presence signals a business domain.
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
    """Build (placeholder_string, params_list) for a NOT IN (...) clause."""
    all_exc = SYSTEM_SCHEMAS | excluded
    params = sorted(all_exc)
    ph = ", ".join(["%s"] * len(params))
    return ph, params


def _fmt_ph(sql_template: str, excluded: set[str]) -> tuple[str, list[str]]:
    """Fill {ph} in a SQL template and return (sql, params)."""
    ph, params = _placeholders(excluded)
    return sql_template.format(ph=ph), params


# ── Schema introspection (async psycopg3) ────────────────────────────────────────

async def introspect_tables(
    conn: psycopg.AsyncConnection,
    excluded_schemas: set[str],
    include_row_counts: bool = True,
) -> dict[str, dict[str, int | None]]:
    """Returns {schema: {table: approx_row_count_or_None}}."""
    tables: dict[str, dict[str, int | None]] = {}

    if include_row_counts:
        try:
            rows = await (await conn.execute(_SQL_TABLES_STATS)).fetchall()
            for row in rows:
                s, t = row["table_schema"], row["table_name"]
                if s not in excluded_schemas and s not in SYSTEM_SCHEMAS:
                    tables.setdefault(s, {})[t] = row["approx_rows"]
            return tables
        except Exception as e:
            log.warning(f"pg_stat_user_tables unavailable ({e}), falling back to information_schema")

    sql, params = _fmt_ph(_SQL_TABLES_FALLBACK, excluded_schemas)
    rows = await (await conn.execute(sql, params)).fetchall()
    for row in rows:
        tables.setdefault(row["table_schema"], {})[row["table_name"]] = None
    return tables


async def introspect_columns(
    conn: psycopg.AsyncConnection,
    excluded_schemas: set[str],
) -> dict[str, list[dict]]:
    """Returns {"schema.table": [col_dict, ...]} in ordinal order."""
    sql, params = _fmt_ph(_SQL_COLUMNS, excluded_schemas)
    rows = await (await conn.execute(sql, params)).fetchall()
    result: dict[str, list[dict]] = {}
    for row in rows:
        key = f"{row['table_schema']}.{row['table_name']}"
        result.setdefault(key, []).append(dict(row))
    return result


async def introspect_primary_keys(
    conn: psycopg.AsyncConnection,
    excluded_schemas: set[str],
) -> dict[str, list[str]]:
    """Returns {"schema.table": [pk_col, ...]} in ordinal order."""
    sql, params = _fmt_ph(_SQL_PRIMARY_KEYS, excluded_schemas)
    rows = await (await conn.execute(sql, params)).fetchall()
    result: dict[str, list[str]] = {}
    for row in rows:
        key = f"{row['table_schema']}.{row['table_name']}"
        result.setdefault(key, []).append(row["column_name"])
    return result


async def introspect_foreign_keys(
    conn: psycopg.AsyncConnection,
    excluded_schemas: set[str],
) -> list[dict]:
    """Returns a flat list of FK dicts with cross-schema support."""
    sql, params = _fmt_ph(_SQL_FOREIGN_KEYS, excluded_schemas)
    rows = await (await conn.execute(sql, params)).fetchall()
    return [dict(row) for row in rows]


async def introspect_unique_constraints(
    conn: psycopg.AsyncConnection,
    excluded_schemas: set[str],
) -> dict[str, list[dict]]:
    """Returns {"schema.table": [{"constraint_name": str, "columns": [str,...]}, ...]}."""
    sql, params = _fmt_ph(_SQL_UNIQUE_CONSTRAINTS, excluded_schemas)
    rows = await (await conn.execute(sql, params)).fetchall()

    raw: dict[str, dict[str, list[str]]] = {}
    for row in rows:
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


async def introspect_check_constraints(
    conn: psycopg.AsyncConnection,
    excluded_schemas: set[str],
) -> dict[str, list[dict]]:
    """Returns {"schema.table": [{"constraint_name": str, "check_clause": str}, ...]}."""
    sql, params = _fmt_ph(_SQL_CHECK_CONSTRAINTS, excluded_schemas)
    rows = await (await conn.execute(sql, params)).fetchall()
    result: dict[str, list[dict]] = {}
    for row in rows:
        key = f"{row['table_schema']}.{row['table_name']}"
        result.setdefault(key, []).append({
            "constraint_name": row["constraint_name"],
            "check_clause": row["check_clause"],
        })
    return result


async def run_introspection(
    conn: psycopg.AsyncConnection,
    excluded_schemas: set[str],
    include_row_counts: bool = True,
) -> dict[str, Any]:
    """Run all introspection queries. Failures are captured in errors, not raised."""
    errors: list[str] = []
    tables: dict = {}
    columns: dict = {}
    primary_keys: dict = {}
    foreign_keys: list = []
    unique_constraints: dict = {}
    check_constraints: dict = {}

    try:
        tables = await introspect_tables(conn, excluded_schemas, include_row_counts)
    except Exception as e:
        errors.append(f"tables: {e}")
        log.error(f"introspect_tables failed: {e}")

    try:
        columns = await introspect_columns(conn, excluded_schemas)
    except Exception as e:
        errors.append(f"columns: {e}")
        log.error(f"introspect_columns failed: {e}")

    try:
        primary_keys = await introspect_primary_keys(conn, excluded_schemas)
    except Exception as e:
        errors.append(f"primary_keys: {e}")
        log.error(f"introspect_primary_keys failed: {e}")

    try:
        foreign_keys = await introspect_foreign_keys(conn, excluded_schemas)
    except Exception as e:
        errors.append(f"foreign_keys: {e}")
        log.error(f"introspect_foreign_keys failed: {e}")

    try:
        unique_constraints = await introspect_unique_constraints(conn, excluded_schemas)
    except Exception as e:
        errors.append(f"unique_constraints: {e}")
        log.error(f"introspect_unique_constraints failed: {e}")

    try:
        check_constraints = await introspect_check_constraints(conn, excluded_schemas)
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
    """Returns list of detected business domains from DOMAIN_INDICATORS."""
    return [
        domain
        for domain, indicators in DOMAIN_INDICATORS.items()
        if any(table_exists(tables, s, t) for s, t in indicators)
    ]


# ── Report data assembly ──────────────────────────────────────────────────────────

def build_fk_index(foreign_keys: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """Build from/to lookup indexes over the FK list."""
    from_idx: dict[str, list[dict]] = defaultdict(list)
    to_idx: dict[str, list[dict]] = defaultdict(list)

    for fk in foreign_keys:
        src_key = f"{fk['table_schema']}.{fk['table_name']}"
        dst_key = f"{fk['foreign_table_schema']}.{fk['foreign_table_name']}"
        from_idx[src_key].append(fk)
        to_idx[dst_key].append(fk)

    return {"from": dict(from_idx), "to": dict(to_idx)}


def describe_column_type(col: dict) -> str:
    """Compact human-readable type string from a column metadata dict."""
    dt = (col.get("data_type") or "").lower()
    if dt in ("character varying", "varchar"):
        ml = col.get("character_maximum_length")
        return f"varchar({ml})" if ml else "varchar"
    if dt == "character":
        ml = col.get("character_maximum_length")
        return f"char({ml})" if ml else "char"
    if dt in ("numeric", "decimal"):
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
    """Per-domain architecture: schemas, core tables, internal/cross-domain FKs."""
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

        for fk_list in fk_index.get("from", {}).values():
            for fk_entry in fk_list:
                src_schema = fk_entry["table_schema"]
                dst_schema = fk_entry["foreign_table_schema"]
                if src_schema in my_schemas:
                    if dst_schema in my_schemas:
                        internal_fks += 1
                    else:
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
    """Combine all introspection results into a single structured dict."""
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
    """Render a Markdown pipe table."""
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
    """Render the full database structure report as Markdown."""
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
                if len(str(default)) > 40:
                    default = str(default)[:37] + "..."
                pk_marker = "PK" if cname in pk_cols else ""
                fk_ref = ""
                if cname in fk_from_here:
                    fk = fk_from_here[cname]
                    fk_ref = f"-> {fk['foreign_table_schema']}.{fk['foreign_table_name']}({fk['foreign_column_name']})"
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
                        f"- `{fk['column_name']}` -> "
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
                        f"({fk['column_name']})` -> `{fk['foreign_column_name']}`"
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
        "## Relationship Map",
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
                    lines.append(f"- `{c['from']}` -> `{c['to']}` (domain: {c['to_domain']})")
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
                f"({fk['column_name']})` -> "
                f"`{fk['foreign_table_schema']}.{fk['foreign_table_name']}"
                f"({fk['foreign_column_name']})` "
                f"-- constraint: `{fk['constraint_name']}`"
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
