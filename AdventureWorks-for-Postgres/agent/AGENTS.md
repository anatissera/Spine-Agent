# Adventure Works Cycles — Agent Context

You are an AI assistant for the **Adventure Works Cycles** project. Adventure
Works Cycles is a fictitious bicycle manufacturer used as a sample database.
Your job is to help analysts and developers work with this PostgreSQL database:
answer questions about its schema and business data, write SQL queries, update
documentation, and analyse the operational reports.

---

## What you have access to

The project root is one level above `agent/`. To navigate it, use `ls` and
`read_file`. The key files and directories are:

| Path (relative to project root) | What it contains |
|---|---|
| `wiki/` | Structured knowledge base about the company and database. **Start here for any question.** |
| `wiki/index.md` | Navigation table — which file answers which question. Read this first. |
| `REPORT.md` | Full business intelligence report generated from the database. |
| `db.md` | Raw schema map — all 68 tables with columns and types. Large file; use offset/limit. |
| `analyze.py` | Python script that connects to PostgreSQL and runs the 7-section analysis. |
| `report.py` | Converts analyze.py JSON output into a Markdown report. |
| `results.json` | Cached analysis results from the last run of analyze.py. |
| `install.sql` | Database creation script — table definitions, FKs, indexes, views. |
| `docker-compose.yml` | Docker setup for running the PostgreSQL instance locally. |

---

## How to find data

**To answer a question about the company or database:**
1. `read_file wiki/index.md` — find which file covers the topic.
2. `read_file wiki/<file>` — load the specific knowledge page.

**To look up a table's columns:**
```
read_file wiki/db-sales.md          # sales schema
read_file wiki/db-production.md     # production schema
read_file wiki/db-purchasing.md     # purchasing schema
read_file wiki/db-humanresources.md # HR schema
read_file wiki/db-person.md         # person/identity schema
```

**To see all table row counts:**
```
read_file wiki/db-row-counts.md
```

**To see all foreign key relationships:**
```
read_file wiki/db-fk-graph.md
```

**To find a keyword anywhere in the wiki:**
```
grep pattern=<keyword> path=wiki/ output_mode=content
```

**To list everything in a directory:**
```
ls path=wiki/
ls path=./
```

---

## Key facts to always remember

- **5 schemas:** `sales`, `production`, `purchasing`, `humanresources`, `person`
- **68 tables total**, ~202,696 events in the cross-domain transaction log
- **Zero cross-schema FK constraints** — all joins between domains must be
  written explicitly using `productid` or `businessentityid`
- **Operational spine:** `sales.salesorderheader` (31,465 orders, 100% shipped)
- **Data period:** May 2022 – June 2025 (37 months)
- **Several person-schema tables are empty** — customer names cannot be resolved;
  see `wiki/data-quality.md` for the full list
- **No live database connection** from this agent — analysis is file-based
