#!/usr/bin/env python3
"""
Converts analyze.py JSON output → REPORT.md
Usage: python report.py [results.json] [REPORT.md]
"""

import json
import sys
from datetime import datetime

INPUT  = sys.argv[1] if len(sys.argv) > 1 else "results.json"
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else "REPORT.md"

with open(INPUT) as f:
    d = json.load(f)

lines = []
def w(*args): lines.append(" ".join(str(a) for a in args))
def nl(): lines.append("")


# ── Header ─────────────────────────────────────────────────────────────────
w("# AdventureWorks — Operational Spine Analysis")
w(f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
nl()
w("## Contents")
w("1. [Schema Map](#1-schema-map)")
w("2. [Row Counts](#2-row-counts)")
w("3. [FK Graph](#3-fk-graph)")
w("4. [Spine Identification](#4-spine-identification)")
w("5. [State Machine Detection](#5-state-machine-detection)")
w("6. [Data Profile](#6-data-profile)")
w("7. [Lifecycle Trace](#7-lifecycle-trace)")
nl()


# ── 1. Schema Map ───────────────────────────────────────────────────────────
w("---")
w("## 1. Schema Map")
nl()
schema_map = d["schema_map"]
for schema in sorted(schema_map):
    tables = schema_map[schema]
    # skip convenience views (schemas pe/hr/pr/pu/sa)
    w(f"### `{schema}`  ({len(tables)} tables/views)")
    nl()
    w("| Table | Columns |")
    w("|-------|---------|")
    for table in sorted(tables):
        cols = tables[table]
        col_str = ", ".join(
            f"`{c['column']}` *{c['type']}*" + (" ⚠️null" if c.get("nullable") else "")
            for c in cols[:6]
        )
        more = f" +{len(cols)-6} more" if len(cols) > 6 else ""
        w(f"| `{table}` | {col_str}{more} |")
    nl()


# ── 2. Row Counts ───────────────────────────────────────────────────────────
w("---")
w("## 2. Row Counts")
nl()
w("| Table | Rows |")
w("|-------|-----:|")
for tbl, n in d["row_counts"].items():
    w(f"| `{tbl}` | {n:,} |")
nl()


# ── 3. FK Graph ─────────────────────────────────────────────────────────────
w("---")
w("## 3. FK Graph")
nl()
edges = d["fk_graph"]
cross = [e for e in edges if e["cross_schema"]]
intra = [e for e in edges if not e["cross_schema"]]
w(f"- **Total FK edges:** {len(edges)}")
w(f"- **Cross-schema:** {len(cross)}")
w(f"- **Intra-schema:** {len(intra)}")
nl()

if cross:
    w("### Cross-schema edges")
    nl()
    w("| From | Column | To | Column |")
    w("|------|--------|----|--------|")
    for e in cross:
        w(f"| `{e['from']}` | `{e['from_col']}` | `{e['to']}` | `{e['to_col']}` |")
    nl()

w("### All FK edges by source table")
nl()
from collections import defaultdict
by_src = defaultdict(list)
for e in edges:
    by_src[e["from"]].append(e)
for src in sorted(by_src):
    w(f"**`{src}`**")
    for e in by_src[src]:
        flag = " *(cross-schema)*" if e["cross_schema"] else ""
        w(f"- `{e['from_col']}` → `{e['to']}`.`{e['to_col']}`{flag}")
    nl()


# ── 4. Spine Identification ─────────────────────────────────────────────────
w("---")
w("## 4. Spine Identification")
nl()
w("> Tables ranked by number of **distinct schemas** that reference them via FK.")
w("> A high `distinct_schemas` score = stronger spine candidate.")
nl()
w("| Table | Referencing Schemas | Distinct Schemas | Inbound FKs | Outbound FKs |")
w("|-------|---------------------|:----------------:|:-----------:|:------------:|")
for s in d["spine"]:
    schemas = ", ".join(f"`{x}`" for x in s["referencing_schemas"]) if s["referencing_schemas"] else "—"
    bold_open  = "**" if s["distinct_schemas"] >= 3 else ""
    bold_close = "**" if s["distinct_schemas"] >= 3 else ""
    w(f"| {bold_open}`{s['table']}`{bold_close} | {schemas} "
      f"| {s['distinct_schemas']} | {s['total_inbound_fks']} | {s['total_outbound_fks']} |")
nl()


# ── 5. State Machines ────────────────────────────────────────────────────────
w("---")
w("## 5. State Machine Detection")
nl()
w("Columns whose name contains `status`, `type`, `flag`, `state`, `reason`, `level`, or `class`.")
nl()
for sm in d["state_machines"]:
    w(f"### `{sm['table']}`.`{sm['column']}` _{sm['type']}_")
    nl()
    w("| Value | Count |")
    w("|-------|------:|")
    for v in sm["values"]:
        w(f"| `{v['value']}` | {v['count']:,} |")
    nl()


# ── 6. Data Profile ──────────────────────────────────────────────────────────
w("---")
w("## 6. Data Profile")
nl()
w("Only columns with `null% > 10` or numeric/date ranges are shown.")
nl()
profile = d["data_profile"]
for tbl, cols in profile.items():
    notable = [c for c in cols if c.get("null_pct", 0) > 10 or "min" in c]
    if not notable:
        continue
    w(f"### `{tbl}`")
    nl()
    w("| Column | Type | Null% | Distinct | Min | Max |")
    w("|--------|------|------:|---------:|-----|-----|")
    for c in notable:
        w(f"| `{c['column']}` | {c['type']} "
          f"| {c.get('null_pct', '')} "
          f"| {c.get('distinct', '')} "
          f"| {c.get('min', '')} "
          f"| {c.get('max', '')} |")
    nl()


# ── 7. Lifecycle Trace ───────────────────────────────────────────────────────
w("---")
w("## 7. Lifecycle Trace")
nl()
w("Traces one order from **Sales → Production → Purchasing**.")
nl()
lc = d["lifecycle"]

if lc.get("pipeline_stats"):
    s = lc["pipeline_stats"][0]
    w("### Pipeline aggregate (all orders)")
    nl()
    w("| Metric | Value |")
    w("|--------|-------|")
    w(f"| Total orders | {s.get('total_orders', 'n/a'):,} |")
    w(f"| Shipped (status=5) | {s.get('shipped', 'n/a'):,} |")
    w(f"| Rejected (status=4) | {s.get('rejected', 'n/a'):,} |")
    w(f"| In-process (status=1) | {s.get('in_process', 'n/a'):,} |")
    w(f"| Avg days to ship | {s.get('avg_days_to_ship', 'n/a')} |")
    w(f"| Avg days to due | {s.get('avg_days_due', 'n/a')} |")
    w(f"| Order date range | {s.get('earliest_order', '?')} → {s.get('latest_order', '?')} |")
    nl()

if lc.get("sample_order"):
    o = lc["sample_order"][0]
    w(f"### Sample order: #{o.get('salesorderid')}  _(highest value shipped)_")
    nl()
    w("| Field | Value |")
    w("|-------|-------|")
    w(f"| Customer | {o.get('customer_name', 'n/a')} |")
    w(f"| Sales rep | {o.get('sales_rep', 'n/a')} |")
    w(f"| Territory | {o.get('territory', 'n/a')} |")
    w(f"| Order date | {o.get('orderdate', '')} |")
    w(f"| Ship date | {o.get('shipdate', '')} |")
    w(f"| Total due | ${float(o.get('totaldue', 0)):,.2f} |")
    nl()

if lc.get("work_orders"):
    w("### Work orders triggered (Production domain)")
    nl()
    w("| WO# | Product | Qty | Start | End |")
    w("|-----|---------|----:|-------|-----|")
    for wo in lc["work_orders"]:
        w(f"| {wo.get('workorderid')} | {wo.get('product', '?')} "
          f"| {wo.get('orderqty')} "
          f"| {str(wo.get('startdate',''))[:10]} "
          f"| {str(wo.get('enddate',''))[:10]} |")
    nl()

if lc.get("purchase_orders"):
    w("### Purchase orders for same products (Purchasing domain)")
    nl()
    w("| PO# | Vendor | Product | Ordered | Received |")
    w("|-----|--------|---------|--------:|---------:|")
    for po in lc["purchase_orders"]:
        w(f"| {po.get('purchaseorderid')} | {po.get('vendor', '?')} "
          f"| {po.get('product', '?')} "
          f"| {po.get('orderqty')} "
          f"| {po.get('receivedqty')} |")
    nl()


# ── Write file ───────────────────────────────────────────────────────────────
with open(OUTPUT, "w") as f:
    f.write("\n".join(lines))

print(f"Written to {OUTPUT}")
