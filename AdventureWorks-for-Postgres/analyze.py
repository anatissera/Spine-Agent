#!/usr/bin/env python3
"""
AdventureWorks Operational Spine Analyzer
==========================================
Connects to the AdventureWorks PostgreSQL database and produces a structured
report across 7 analysis sections:

  1. Schema map       — all schemas, tables, columns
  2. Row counts       — per table, sorted descending
  3. FK graph         — all relationships and cross-schema edges
  4. Spine ID         — tables ranked by cross-schema FK reference density
  5. State machines   — status/flag/type columns with value distributions
  6. Data profile     — null rates, numeric ranges, date spans, cardinality
  7. Lifecycle trace  — SalesOrder → WorkOrder → PurchaseOrder temporal chain

Usage:
  python analyze.py [--host HOST] [--port PORT] [--db DB]
                    [--user USER] [--password PASSWORD]
                    [--output FILE]   # optional JSON export

Defaults: host=localhost, port=5432, db=Adventureworks,
          user=postgres, password=postgres
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    sys.exit("psycopg2 not found. Install it with:  pip install psycopg2-binary")


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def connect(host, port, db, user, password):
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=db,
            user=user, password=password,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        conn.autocommit = True
        return conn
    except psycopg2.OperationalError as e:
        sys.exit(f"[ERROR] Could not connect to database: {e}")


def q(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# ---------------------------------------------------------------------------
# Section 1 — Schema Map
# ---------------------------------------------------------------------------

ANALYSIS_SCHEMAS = ("person", "humanresources", "production", "purchasing", "sales")


def schema_map(conn):
    rows = q(conn, """
        SELECT
            c.table_schema   AS schema,
            c.table_name     AS table_name,
            c.column_name    AS column_name,
            c.data_type      AS data_type,
            c.is_nullable    AS nullable,
            c.character_maximum_length AS max_len,
            c.column_default AS col_default
        FROM information_schema.columns c
        WHERE c.table_schema = ANY(%s)
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
    """, (list(ANALYSIS_SCHEMAS),))

    result = defaultdict(lambda: defaultdict(list))
    for r in rows:
        result[r["schema"]][r["table_name"]].append({
            "column":   r["column_name"],
            "type":     r["data_type"],
            "nullable": r["nullable"] == "YES",
            "max_len":  r["max_len"],
            "default":  r["col_default"],
        })
    return result


# ---------------------------------------------------------------------------
# Section 2 — Row Counts
# ---------------------------------------------------------------------------

def row_counts(conn, schema_map_data):
    counts = {}
    for schema, tables in schema_map_data.items():
        for table in tables:
            rows = q(conn, f'SELECT COUNT(*) AS n FROM "{schema}"."{table}"')
            counts[f"{schema}.{table}"] = rows[0]["n"]
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


# ---------------------------------------------------------------------------
# Section 3 — FK Graph
# ---------------------------------------------------------------------------

def fk_graph(conn):
    rows = q(conn, """
        SELECT
            kcu.table_schema        AS src_schema,
            kcu.table_name          AS src_table,
            kcu.column_name         AS src_col,
            ccu.table_schema        AS ref_schema,
            ccu.table_name          AS ref_table,
            ccu.column_name         AS ref_col,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema    = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = ANY(%s)
        ORDER BY src_schema, src_table, src_col
    """, (list(ANALYSIS_SCHEMAS),))

    edges = []
    for r in rows:
        edges.append({
            "from":        f"{r['src_schema']}.{r['src_table']}",
            "from_col":    r["src_col"],
            "to":          f"{r['ref_schema']}.{r['ref_table']}",
            "to_col":      r["ref_col"],
            "cross_schema": r["src_schema"] != r["ref_schema"],
        })
    return edges


# ---------------------------------------------------------------------------
# Section 4 — Spine Identification (cross-schema reference density)
# ---------------------------------------------------------------------------

def spine_identification(fk_edges):
    """
    For each table, count how many DISTINCT source schemas point to it via FK.
    A table referenced from 3 different schemas is a stronger spine candidate
    than one referenced 10 times from the same schema.
    """
    # inbound[target_table] = set of source schemas
    inbound_schemas = defaultdict(set)
    inbound_count   = defaultdict(int)
    outbound_count  = defaultdict(int)

    for e in fk_edges:
        inbound_schemas[e["to"]].add(e["from"].split(".")[0])
        inbound_count[e["to"]] += 1
        outbound_count[e["from"]] += 1

    scores = []
    all_tables = set(inbound_schemas) | set(outbound_count)
    for tbl in all_tables:
        src_schemas = inbound_schemas.get(tbl, set())
        scores.append({
            "table":               tbl,
            "referencing_schemas": sorted(src_schemas),
            "distinct_schemas":    len(src_schemas),
            "total_inbound_fks":   inbound_count.get(tbl, 0),
            "total_outbound_fks":  outbound_count.get(tbl, 0),
        })

    scores.sort(key=lambda x: (-x["distinct_schemas"], -x["total_inbound_fks"]))
    return scores


# ---------------------------------------------------------------------------
# Section 5 — State Machine Detection
# ---------------------------------------------------------------------------

STATUS_KEYWORDS = ("status", "flag", "type", "state", "reason", "level", "class")


def state_machines(conn, schema_map_data):
    results = []
    for schema, tables in schema_map_data.items():
        for table, columns in tables.items():
            for col in columns:
                col_lower = col["column"].lower()
                if any(kw in col_lower for kw in STATUS_KEYWORDS):
                    # Skip pure boolean flags — only interesting if they're
                    # integer or varchar enums
                    if col["type"] in ("boolean",):
                        continue
                    try:
                        rows = q(conn, f"""
                            SELECT "{col['column']}" AS val, COUNT(*) AS n
                            FROM "{schema}"."{table}"
                            GROUP BY "{col['column']}"
                            ORDER BY n DESC
                            LIMIT 20
                        """)
                        values = [{"value": r["val"], "count": r["n"]} for r in rows]
                    except Exception:
                        values = []
                    if values:
                        results.append({
                            "table":  f"{schema}.{table}",
                            "column": col["column"],
                            "type":   col["type"],
                            "values": values,
                        })
    return results


# ---------------------------------------------------------------------------
# Section 6 — Data Profile
# ---------------------------------------------------------------------------

def data_profile(conn, schema_map_data):
    profile = {}
    for schema, tables in schema_map_data.items():
        for table, columns in tables.items():
            key = f"{schema}.{table}"
            profile[key] = []
            for col in columns:
                col_name = col["column"]
                dtype    = col["type"]
                entry = {"column": col_name, "type": dtype}

                try:
                    # Null rate
                    total = q(conn, f'SELECT COUNT(*) AS n FROM "{schema}"."{table}"')[0]["n"]
                    nulls = q(conn, f"""
                        SELECT COUNT(*) AS n FROM "{schema}"."{table}"
                        WHERE "{col_name}" IS NULL
                    """)[0]["n"]
                    entry["null_pct"] = round(nulls / total * 100, 1) if total else 0

                    # Cardinality (distinct count)
                    dist = q(conn, f"""
                        SELECT COUNT(DISTINCT "{col_name}") AS n
                        FROM "{schema}"."{table}"
                    """)[0]["n"]
                    entry["distinct"] = dist

                    # Numeric stats
                    if dtype in ("integer", "smallint", "bigint", "numeric",
                                 "real", "double precision", "money"):
                        stats = q(conn, f"""
                            SELECT MIN("{col_name}")::numeric AS mn,
                                   MAX("{col_name}")::numeric AS mx,
                                   AVG("{col_name}")::numeric AS avg
                            FROM "{schema}"."{table}"
                        """)[0]
                        entry["min"] = float(stats["mn"]) if stats["mn"] is not None else None
                        entry["max"] = float(stats["mx"]) if stats["mx"] is not None else None
                        entry["avg"] = round(float(stats["avg"]), 2) if stats["avg"] is not None else None

                    # Date stats
                    elif dtype in ("date", "timestamp without time zone",
                                   "timestamp with time zone"):
                        stats = q(conn, f"""
                            SELECT MIN("{col_name}") AS mn,
                                   MAX("{col_name}") AS mx
                            FROM "{schema}"."{table}"
                        """)[0]
                        entry["min"] = str(stats["mn"]) if stats["mn"] else None
                        entry["max"] = str(stats["mx"]) if stats["mx"] else None

                except Exception:
                    pass

                profile[key].append(entry)

    return profile


# ---------------------------------------------------------------------------
# Section 7 — Lifecycle Trace (SalesOrder → WorkOrder → PurchaseOrder)
# ---------------------------------------------------------------------------

def lifecycle_trace(conn):
    """
    Follow a sample SalesOrderHeader through Production and Purchasing to show
    how the same business event creates downstream objects across domains.
    Also produces aggregate temporal statistics for the full order pipeline.
    """
    # Aggregate timing across the pipeline
    pipeline_stats = q(conn, """
        SELECT
            AVG(EXTRACT(EPOCH FROM (soh.shipdate   - soh.orderdate))  / 86400)::numeric(10,1) AS avg_days_to_ship,
            AVG(EXTRACT(EPOCH FROM (soh.duedate    - soh.orderdate))  / 86400)::numeric(10,1) AS avg_days_due,
            MIN(soh.orderdate)  AS earliest_order,
            MAX(soh.orderdate)  AS latest_order,
            COUNT(*)            AS total_orders,
            SUM(CASE WHEN soh.status = 5 THEN 1 ELSE 0 END) AS shipped,
            SUM(CASE WHEN soh.status = 4 THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN soh.status = 1 THEN 1 ELSE 0 END) AS in_process
        FROM sales.salesorderheader soh
    """)

    # Sample: one order and its cross-domain footprint
    sample_order = q(conn, """
        SELECT
            soh.salesorderid,
            soh.orderdate,
            soh.duedate,
            soh.shipdate,
            soh.status,
            soh.totaldue,
            p.firstname || ' ' || p.lastname AS customer_name,
            sp_person.firstname || ' ' || sp_person.lastname AS sales_rep,
            st.name AS territory
        FROM sales.salesorderheader soh
        JOIN sales.customer c           ON c.customerid       = soh.customerid
        LEFT JOIN person.person p       ON p.businessentityid = c.personid
        JOIN sales.salesterritory st    ON st.territoryid     = soh.territoryid
        LEFT JOIN sales.salesperson sp  ON sp.businessentityid = soh.salespersonid
        LEFT JOIN person.person sp_person ON sp_person.businessentityid = sp.businessentityid
        WHERE soh.status = 5
        ORDER BY soh.totaldue DESC
        LIMIT 1
    """)

    work_orders = []
    purchase_orders = []

    if sample_order:
        order_id = sample_order[0]["salesorderid"]

        # WorkOrders triggered by this sale's products
        work_orders = q(conn, """
            SELECT
                wo.workorderid,
                pr.name AS product,
                wo.orderqty,
                wo.startdate,
                wo.enddate,
                wo.duedate,
                wo.scrappedqty,
                sr.name AS scrap_reason
            FROM production.workorder wo
            JOIN production.product pr ON pr.productid = wo.productid
            LEFT JOIN production.scrapreason sr ON sr.scrapreasonid = wo.scrapreasonid
            WHERE wo.productid IN (
                SELECT sod.productid
                FROM sales.salesorderdetail sod
                WHERE sod.salesorderid = %s
            )
            ORDER BY wo.startdate
            LIMIT 10
        """, (order_id,))

        # PurchaseOrders for the same products
        purchase_orders = q(conn, """
            SELECT
                poh.purchaseorderid,
                poh.orderdate,
                poh.shipdate,
                poh.status       AS po_status,
                v.name           AS vendor,
                pod.orderqty,
                pr.name          AS product,
                pod.unitprice,
                pod.receivedqty,
                pod.rejectedqty
            FROM purchasing.purchaseorderheader poh
            JOIN purchasing.purchaseorderdetail pod ON pod.purchaseorderid = poh.purchaseorderid
            JOIN production.product pr              ON pr.productid        = pod.productid
            JOIN purchasing.vendor v                ON v.businessentityid  = poh.vendorid
            WHERE pod.productid IN (
                SELECT sod.productid
                FROM sales.salesorderdetail sod
                WHERE sod.salesorderid = %s
            )
            ORDER BY poh.orderdate
            LIMIT 10
        """, (order_id,))

    return {
        "pipeline_stats":   [dict(r) for r in pipeline_stats],
        "sample_order":     [dict(r) for r in sample_order],
        "work_orders":      [dict(r) for r in work_orders],
        "purchase_orders":  [dict(r) for r in purchase_orders],
    }


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
DIM    = "\033[2m"


def hdr(title, char="="):
    width = 72
    print(f"\n{BOLD}{CYAN}{char * width}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{char * width}{RESET}")


def sub(title):
    print(f"\n{BOLD}{YELLOW}  ── {title}{RESET}")


def row_fmt(label, value, indent=4):
    pad = " " * indent
    print(f"{pad}{DIM}{label:<30}{RESET}{value}")


def print_report(results):
    print(f"\n{BOLD}AdventureWorks — Operational Spine Analysis{RESET}")
    print(f"{DIM}Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")

    # ── 1. Schema Map ──────────────────────────────────────────────────────
    hdr("1. SCHEMA MAP")
    sm = results["schema_map"]
    for schema in sorted(sm):
        tables = sm[schema]
        sub(f"{schema}  ({len(tables)} tables)")
        for table, cols in sorted(tables.items()):
            col_summary = ", ".join(
                f"{c['column']} [{c['type']}]" for c in cols[:5]
            )
            more = f"  +{len(cols)-5} more" if len(cols) > 5 else ""
            print(f"      {GREEN}{table:<40}{RESET}{col_summary}{DIM}{more}{RESET}")

    # ── 2. Row Counts ──────────────────────────────────────────────────────
    hdr("2. ROW COUNTS  (top 20)")
    rc = results["row_counts"]
    for i, (tbl, n) in enumerate(list(rc.items())[:20]):
        bar = "█" * min(40, n // 500)
        print(f"    {tbl:<45} {n:>8,}  {DIM}{bar}{RESET}")

    # ── 3. FK Graph ────────────────────────────────────────────────────────
    hdr("3. FK GRAPH")
    edges = results["fk_graph"]
    cross = [e for e in edges if e["cross_schema"]]
    intra = [e for e in edges if not e["cross_schema"]]
    print(f"    Total FK edges : {len(edges)}")
    print(f"    Cross-schema   : {BOLD}{RED}{len(cross)}{RESET}  ← these wire domains together")
    print(f"    Intra-schema   : {len(intra)}")
    sub("Cross-schema edges")
    for e in cross:
        print(f"      {e['from']}.{e['from_col']:<35} → "
              f"{e['to']}.{e['to_col']}")

    # ── 4. Spine Identification ────────────────────────────────────────────
    hdr("4. SPINE IDENTIFICATION  (by cross-schema reference density)")
    print(f"    {DIM}Higher distinct_schemas = stronger spine candidate{RESET}\n")
    spine = results["spine"]
    print(f"    {'TABLE':<45} {'DIST_SCHEMAS':>12} {'INBOUND_FKS':>12} {'OUTBOUND_FKS':>13}")
    print(f"    {'-'*45} {'-'*12} {'-'*12} {'-'*13}")
    for s in spine[:15]:
        schemas_str = ", ".join(s["referencing_schemas"]) if s["referencing_schemas"] else "—"
        highlight = BOLD + RED if s["distinct_schemas"] >= 3 else (
                    YELLOW if s["distinct_schemas"] == 2 else RESET)
        print(f"    {highlight}{s['table']:<45}{RESET}"
              f" {s['distinct_schemas']:>12}"
              f" {s['total_inbound_fks']:>12}"
              f" {s['total_outbound_fks']:>13}"
              f"  {DIM}{schemas_str}{RESET}")

    # ── 5. State Machines ──────────────────────────────────────────────────
    hdr("5. STATE MACHINE DETECTION")
    for sm_entry in results["state_machines"]:
        vals = "  ".join(
            f"{v['value']}({v['count']:,})" for v in sm_entry["values"][:8]
        )
        print(f"    {GREEN}{sm_entry['table']}.{sm_entry['column']}{RESET}"
              f"  [{sm_entry['type']}]")
        print(f"      {DIM}{vals}{RESET}")

    # ── 6. Data Profile ────────────────────────────────────────────────────
    hdr("6. DATA PROFILE  (columns with notable null rates or ranges)")
    profile = results["data_profile"]
    printed = 0
    for tbl, cols in profile.items():
        notable = [c for c in cols if (
            c.get("null_pct", 0) > 10
            or "min" in c
        )]
        if not notable:
            continue
        if printed == 0:
            print(f"    {'TABLE.COLUMN':<50} {'TYPE':<12} {'NULL%':>6} {'DISTINCT':>9} {'MIN':>20} {'MAX':>20}")
            print(f"    {'-'*50} {'-'*12} {'-'*6} {'-'*9} {'-'*20} {'-'*20}")
        for c in notable:
            label = f"{tbl}.{c['column']}"
            print(f"    {label:<50} {c['type']:<12}"
                  f" {c.get('null_pct', ''):>6}"
                  f" {c.get('distinct', ''):>9}"
                  f" {str(c.get('min', '')):>20}"
                  f" {str(c.get('max', '')):>20}")
        printed += 1

    # ── 7. Lifecycle Trace ────────────────────────────────────────────────
    hdr("7. LIFECYCLE TRACE  — SalesOrder → WorkOrder → PurchaseOrder")
    lc = results["lifecycle"]

    if lc["pipeline_stats"]:
        s = lc["pipeline_stats"][0]
        sub("Pipeline aggregate stats (all orders)")
        row_fmt("Total orders:",         f"{s.get('total_orders', 'n/a'):,}")
        row_fmt("Shipped (status=5):",   f"{s.get('shipped', 'n/a'):,}")
        row_fmt("Rejected (status=4):",  f"{s.get('rejected', 'n/a'):,}")
        row_fmt("In-process (status=1):",f"{s.get('in_process', 'n/a'):,}")
        row_fmt("Avg days to ship:",     s.get('avg_days_to_ship', 'n/a'))
        row_fmt("Avg days to due:",      s.get('avg_days_due', 'n/a'))
        row_fmt("Order date range:",     f"{s.get('earliest_order', '?')} → {s.get('latest_order', '?')}")

    if lc["sample_order"]:
        o = lc["sample_order"][0]
        sub(f"Sample order: #{o.get('salesorderid', '?')}  (highest value shipped)")
        row_fmt("Customer:",    o.get("customer_name", "n/a"))
        row_fmt("Sales rep:",   o.get("sales_rep", "n/a"))
        row_fmt("Territory:",   o.get("territory", "n/a"))
        row_fmt("Order date:",  str(o.get("orderdate", "")))
        row_fmt("Ship date:",   str(o.get("shipdate", "")))
        row_fmt("Total due:",   f"${float(o.get('totaldue', 0)):,.2f}")

    if lc["work_orders"]:
        sub("Work orders triggered for same products (Production domain)")
        for wo in lc["work_orders"][:5]:
            print(f"      WO#{wo.get('workorderid')}  {wo.get('product','?'):<35}"
                  f"  qty={wo.get('orderqty')}  "
                  f"{str(wo.get('startdate',''))[:10]} → {str(wo.get('enddate',''))[:10]}")

    if lc["purchase_orders"]:
        sub("Purchase orders for same products (Purchasing domain)")
        for po in lc["purchase_orders"][:5]:
            print(f"      PO#{po.get('purchaseorderid')}  {po.get('vendor','?'):<30}"
                  f"  {po.get('product','?')[:25]:<25}"
                  f"  qty={po.get('orderqty')}  rcvd={po.get('receivedqty')}")

    print(f"\n{BOLD}{GREEN}Analysis complete.{RESET}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AdventureWorks Operational Spine Analyzer")
    parser.add_argument("--host",     default="localhost")
    parser.add_argument("--port",     type=int, default=5432)
    parser.add_argument("--db",       default="Adventureworks")
    parser.add_argument("--user",     default="postgres")
    parser.add_argument("--password", default="postgres")
    parser.add_argument("--output",   default=None,
                        help="Optional path to write full results as JSON")
    args = parser.parse_args()

    print(f"{DIM}Connecting to {args.host}:{args.port}/{args.db} as {args.user}…{RESET}")
    conn = connect(args.host, args.port, args.db, args.user, args.password)
    print(f"{GREEN}Connected.{RESET}")

    print(f"{DIM}[1/7] Schema map…{RESET}", end=" ", flush=True)
    sm = schema_map(conn)
    print("done")

    print(f"{DIM}[2/7] Row counts…{RESET}", end=" ", flush=True)
    rc = row_counts(conn, sm)
    print("done")

    print(f"{DIM}[3/7] FK graph…{RESET}", end=" ", flush=True)
    fk = fk_graph(conn)
    print("done")

    print(f"{DIM}[4/7] Spine identification…{RESET}", end=" ", flush=True)
    spine = spine_identification(fk)
    print("done")

    print(f"{DIM}[5/7] State machine detection…{RESET}", end=" ", flush=True)
    sm_data = state_machines(conn, sm)
    print("done")

    print(f"{DIM}[6/7] Data profile…{RESET}", end=" ", flush=True)
    profile = data_profile(conn, sm)
    print("done")

    print(f"{DIM}[7/7] Lifecycle trace…{RESET}", end=" ", flush=True)
    lc = lifecycle_trace(conn)
    print("done")

    results = {
        "schema_map":     {s: {t: cols for t, cols in tables.items()}
                           for s, tables in sm.items()},
        "row_counts":     rc,
        "fk_graph":       fk,
        "spine":          spine,
        "state_machines": sm_data,
        "data_profile":   profile,
        "lifecycle":      lc,
    }

    print_report(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"{DIM}Full results written to {args.output}{RESET}\n")

    conn.close()


if __name__ == "__main__":
    main()
