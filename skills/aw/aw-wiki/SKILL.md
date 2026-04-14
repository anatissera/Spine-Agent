---
name: aw-wiki
description: >
  Use this skill when asked anything about Adventure Works Cycles — the company,
  its business metrics, schemas, tables, columns, foreign keys, operational
  performance, data quality issues, or how the domains connect. Activate on
  questions like "what tables are in the sales schema?", "how does production
  link to purchasing?", "what is the company's gross margin?", "which table
  tracks work orders?", "what are the known data gaps?", or "explain the spine".
  This skill is read-only — it never writes or modifies files.
metadata: {}
---

# Skill: AW Wiki

## What This Skill Does

Navigates the `wiki/` knowledge base to answer questions about Adventure Works
Cycles — the company, its data, and its PostgreSQL database schema. Every topic
has a dedicated file; this skill tells you which one to read for each question.

---

## Navigation Rules

**Always start with `wiki/index.md`.** It contains the full navigation table
and a quick-reference metrics summary. Use it to decide which files to read next.

| Question type | File to read |
|---|---|
| What does the company do? Scale, channels, geography? | `wiki/company-overview.md` |
| Revenue, margins, customers, order volume, territories | `wiki/business-metrics.md` |
| Fulfillment rate, SLA, scrap, vendor quality, production efficiency | `wiki/operational-health.md` |
| What is the operational spine? How does work flow? | `wiki/spine.md` |
| Known empty tables, data gaps, quality flags | `wiki/data-quality.md` |
| `sales` schema — tables, columns, FKs, row counts | `wiki/db-sales.md` |
| `production` schema — tables, columns, FKs, row counts | `wiki/db-production.md` |
| `purchasing` schema — tables, columns, FKs, row counts | `wiki/db-purchasing.md` |
| `humanresources` schema — tables, columns, FKs | `wiki/db-humanresources.md` |
| `person` schema — tables, columns, FKs | `wiki/db-person.md` |
| Row counts for every table | `wiki/db-row-counts.md` |
| All foreign key relationships across schemas | `wiki/db-fk-graph.md` |
| Status/type columns with value distributions | `wiki/state-machines.md` |
| Transaction history structure and lifecycle trace | `wiki/event-log.md` |

---

## How to Answer

1. Read `wiki/index.md` first to orient.
2. Read only the files relevant to the question — do not load all files.
3. Lead with the answer, not the file path.
4. Be explicit when citing a specific metric vs. making an inference.
5. If two files seem relevant, read both before answering.

---

## Key Facts to Keep in Mind

- **No cross-schema FK constraints.** All 65 declared FKs are intra-schema.
  Cross-domain joins must be written explicitly using `productid` or
  `businessentityid`.
- **Several person-schema tables are empty** in this dataset (person,
  businessentity, store, emailaddress). Customer names cannot be resolved.
  See `wiki/data-quality.md`.
- The **operational spine** is `sales.salesorderheader`. See `wiki/spine.md`.

---

## Constraints

- Read-only — this skill never calls write_file or edit_file.
- Do not guess column names or FKs — read the relevant schema file first.
- Do not confuse `wiki/` documentation (static) with live database state.
