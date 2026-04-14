# Prompt: Generate Periodic Collector for `analyze_company_config`

## Context

This extends `PROMPT_db_config_report_skill.md`. That file defines the
`analyze_company_config` skill, which introspects a PostgreSQL database and produces a
Business Configuration Report. The problem: running all those SQL aggregation queries on
every agent invocation is slow and wastes resources — and the data changes slowly (daily
at most for most metrics).

**Goal:** implement a standalone collector that runs the SQL queries on a schedule,
persists the raw results to a cache table in the `spine_agent` schema, and make the skill
read from cache instead of querying live every time.

The LLM (Claude API) is **never involved in the collector** — it is pure Python + SQL.
The collector is infrastructure; the skill is the consumer.

---

## What to Build

Four artifacts, in order of dependency:

```
collectors/
└── company_config_collector.py   # Standalone script — runs SQL, writes to cache

agent/
└── scheduler.py                  # APScheduler setup that runs the collector on cron

db/
└── migrations/
    └── 002_company_config_cache.sql  # New table in spine_agent schema

skills/builtin/analyze_company_config/
└── code.py                       # MODIFY: add cache-read path before live queries
```

---

## 1. Cache Table — `002_company_config_cache.sql`

Create this file at `db/migrations/002_company_config_cache.sql`:

```sql
-- Cache table for periodic business configuration snapshots.
-- Populated by collectors/company_config_collector.py on a schedule.
-- Read by the analyze_company_config skill (cache-aside pattern).

CREATE TABLE IF NOT EXISTS spine_agent.company_config_snapshots (
    id                  SERIAL PRIMARY KEY,
    collected_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collector_version   TEXT NOT NULL DEFAULT '1.0.0',
    domains_detected    TEXT[]  NOT NULL,           -- e.g. ARRAY['sales','hr','production']
    raw_metrics         JSONB   NOT NULL,           -- per-domain raw query results
    report              JSONB   NOT NULL,           -- fully assembled report object
    markdown_summary    TEXT    NOT NULL,           -- pre-rendered Markdown
    confidence          TEXT    NOT NULL,           -- high | medium | low
    collection_duration_ms INTEGER,
    error_log           JSONB   DEFAULT '[]'::jsonb -- non-fatal errors during collection
);

-- Only keep the last 30 snapshots (one month of daily runs)
CREATE INDEX IF NOT EXISTS idx_snapshots_collected_at
    ON spine_agent.company_config_snapshots (collected_at DESC);

-- Helper: fetch the latest snapshot not older than N hours
-- Usage: SELECT * FROM spine_agent.latest_config_snapshot(6);
CREATE OR REPLACE FUNCTION spine_agent.latest_config_snapshot(max_age_hours INT DEFAULT 6)
RETURNS TABLE (
    id INT, collected_at TIMESTAMPTZ, domains_detected TEXT[],
    raw_metrics JSONB, report JSONB, markdown_summary TEXT,
    confidence TEXT, collection_duration_ms INT
) AS $$
    SELECT id, collected_at, domains_detected, raw_metrics, report,
           markdown_summary, confidence, collection_duration_ms
    FROM spine_agent.company_config_snapshots
    WHERE collected_at >= NOW() - (max_age_hours || ' hours')::INTERVAL
    ORDER BY collected_at DESC
    LIMIT 1;
$$ LANGUAGE sql STABLE;

-- Cleanup: auto-delete snapshots older than 30 days
CREATE OR REPLACE FUNCTION spine_agent.cleanup_old_snapshots()
RETURNS void AS $$
    DELETE FROM spine_agent.company_config_snapshots
    WHERE collected_at < NOW() - INTERVAL '30 days';
$$ LANGUAGE sql;
```

---

## 2. Collector Script — `collectors/company_config_collector.py`

This is a **standalone Python script** with zero LLM dependency.
It runs all the SQL queries from the skill, assembles the report dict and Markdown,
and writes a new row to `spine_agent.company_config_snapshots`.

### File header and imports

```python
#!/usr/bin/env python3
"""
company_config_collector.py

Periodic collector for the Business Configuration Report.
Runs SQL aggregation queries against the company database,
assembles a structured report, and writes it to the
spine_agent.company_config_snapshots cache table.

Designed to run on a schedule (APScheduler or system cron).
No LLM calls. Pure Python + psycopg2.

Usage:
    python collectors/company_config_collector.py            # run once
    python collectors/company_config_collector.py --dry-run  # run but don't write to DB
    python collectors/company_config_collector.py --force    # ignore cache age, always run
"""

import os
import sys
import json
import time
import logging
import argparse
import traceback
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
log = logging.getLogger("company_config_collector")

COLLECTOR_VERSION = "1.0.0"
DEFAULT_CACHE_TTL_HOURS = 6       # Skip run if a snapshot this fresh already exists
DEFAULT_KEEP_SNAPSHOTS = 30       # Delete snapshots older than this many days
DEFAULT_REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
LATEST_REPORT_FILENAME = "company_config_latest.md"
MAX_REPORT_FILES = 7              # Keep last N timestamped .md files, delete older ones
```

### Schema discovery function

```python
def discover_schema(cur) -> dict[str, list[str]]:
    """
    Returns {schema_name: [table_name, ...]} for all non-system schemas.
    Also returns column names per table as a nested dict.
    """
    cur.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
          AND table_type = 'BASE TABLE'
        ORDER BY table_schema, table_name;
    """)
    schema_map: dict[str, list[str]] = {}
    for row in cur.fetchall():
        schema_map.setdefault(row["table_schema"], []).append(row["table_name"])

    # Column map: {schema.table: [col_name, ...]}
    cur.execute("""
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY table_schema, table_name, ordinal_position;
    """)
    col_map: dict[str, list[str]] = {}
    for row in cur.fetchall():
        key = f"{row['table_schema']}.{row['table_name']}"
        col_map.setdefault(key, []).append(row["column_name"])

    return schema_map, col_map


def table_exists(schema_map: dict, schema: str, table: str) -> bool:
    return table in schema_map.get(schema, [])
```

### Domain detection function

```python
DOMAIN_INDICATORS = {
    "sales":      [("sales", "salesorderheader"), ("sales", "customer")],
    "hr":         [("humanresources", "employee"), ("humanresources", "department")],
    "production": [("production", "product"), ("production", "workorder")],
    "purchasing": [("purchasing", "vendor"), ("purchasing", "purchaseorderheader")],
    "person":     [("person", "person"), ("person", "address")],
    "geography":  [("sales", "salesterritory"), ("person", "stateprovince")],
    "finance":    [("sales", "currencyrate"), ("sales", "salestaxrate")],
}

def detect_domains(schema_map: dict) -> list[str]:
    detected = []
    for domain, indicators in DOMAIN_INDICATORS.items():
        if any(table_exists(schema_map, s, t) for s, t in indicators):
            detected.append(domain)
    return detected
```

### Per-domain query functions

Each function takes `(cur, schema_map)` and returns a dict of raw metric values.
Each query is wrapped in try/except — a failed query appends to `errors` list and
the function continues. Functions return `None` if the domain's core table is absent.

Implement one function per domain. Name them `collect_sales`, `collect_hr`,
`collect_production`, `collect_purchasing`, `collect_geography`, `collect_finance`.

**`collect_sales(cur, schema_map) -> dict | None`**

Run the following queries (each in its own try/except block):
- Volume + revenue: `COUNT(*)`, `MIN/MAX(orderdate)`, `AVG/SUM(subtotal)`, `COUNT(DISTINCT customerid)` from `sales.salesorderheader`
- Status distribution: `SELECT status, COUNT(*) FROM sales.salesorderheader GROUP BY status`
- Online/offline split: `SELECT onlineorderflag, COUNT(*) FROM sales.salesorderheader GROUP BY onlineorderflag`
- Top 5 territories (if `sales.salesterritory` exists): join `salesorderheader` → `salesterritory`, group by `t.name`, order by `SUM(subtotal) DESC LIMIT 5`
- Active special offers count + avg discount (if `sales.specialoffer` exists): `COUNT(*) FILTER (WHERE CURRENT_DATE BETWEEN startdate AND enddate)`
- Sales per year: `SELECT EXTRACT(YEAR FROM orderdate) AS yr, COUNT(*), ROUND(SUM(subtotal)::numeric,2) FROM sales.salesorderheader GROUP BY yr ORDER BY yr`

Return all results in a flat dict. Include `errors: list[str]` for any failed sub-query.

**`collect_hr(cur, schema_map) -> dict | None`**

- Headcount: `COUNT(*)`, `COUNT(*) FILTER (WHERE currentflag)`, salaried vs hourly split, avg tenure from `humanresources.employee`
- Department breakdown (if `humanresources.employeedepartmenthistory` and `department` exist): `GROUP BY d.name, d.groupname` where `enddate IS NULL`
- Pay stats (if `humanresources.employeepayhistory` exists): `MIN/MAX/AVG(rate)` on latest pay record per employee (subquery on `MAX(ratechangedate)`)

**`collect_production(cur, schema_map) -> dict | None`**

- Product catalog: `COUNT(*)`, `COUNT(*) FILTER (WHERE finishedgoodsflag)`, `COUNT(*) FILTER (WHERE makeflag)`, `AVG(listprice)`, `AVG(standardcost)` from `production.product` where active
- Category breakdown (if `productsubcategory` and `productcategory` exist)
- Inventory health (if `production.productinventory` exists): total units, count of products at/below reorder point
- Work order stats (if `production.workorder` exists): count, avg batch size, on-time rate

**`collect_purchasing(cur, schema_map) -> dict | None`**

- Vendor stats: `COUNT(*)`, active count, preferred count, `AVG(creditrating)` from `purchasing.vendor`
- PO volume/spend (if `purchasing.purchaseorderheader` exists)
- Lead time stats (if `purchasing.productvendor` exists): `AVG/MIN/MAX(averageleadtime)`

**`collect_geography(cur, schema_map) -> dict | None`**

- Revenue by region group: join `sales.salesterritory` → `sales.salesorderheader`, group by `t.group`
- Country count: from `person.countryregion` if present

**`collect_finance(cur, schema_map) -> dict | None`**

- Currency count (if `sales.currencyrate` exists): `COUNT(DISTINCT currencycode)`
- Tax jurisdictions (if `sales.salestaxrate` exists): `COUNT(DISTINCT stateprovinceid)`, `AVG(taxrate)`

### Report assembly function

```python
def assemble_report(domains: list[str], metrics: dict[str, dict]) -> dict:
    """
    Takes raw per-domain metrics dicts and produces the structured report.
    The insights (plain-language bullets) are generated by deterministic rules,
    NOT by an LLM — so this function must contain explicit if/else logic.
    """
```

**Insight generation rules (deterministic, no LLM):**

| Domain | Metric | Insight rule |
|---|---|---|
| sales | `avg_order_value` | < 100 → "budget-tier pricing"; 100–1000 → "mid-market"; > 1000 → "premium/enterprise pricing" |
| sales | `online_ratio` | > 0.7 → "primarily online channel"; < 0.3 → "primarily in-person/B2B channel"; else → "hybrid channel mix" |
| sales | `active_years` (max_date - min_date in years) | > 10 → "mature operations"; 3–10 → "established"; < 3 → "early-stage" |
| hr | `salaried_ratio` | > 0.7 → "primarily knowledge-worker org"; < 0.3 → "primarily hourly/operational workforce" |
| hr | `avg_tenure_years` | > 5 → "low turnover / stable org"; < 2 → "high turnover signal" |
| hr | top department `groupname` | "Manufacturing" → "production-heavy org"; "Sales and Marketing" → "sales-led org" |
| production | `make_ratio` (manufactured_inhouse / total) | > 0.6 → "vertically integrated manufacturing"; < 0.2 → "primarily assembly/reseller model" |
| production | `stockout_ratio` (products_at_reorder / total_tracked) | > 0.2 → "inventory risk: 20%+ SKUs at reorder point"; < 0.05 → "healthy inventory levels" |
| purchasing | `preferred_vendor_ratio` | > 0.5 → "strong vendor partnerships"; < 0.2 → "broad/undifferentiated supplier base" |
| purchasing | `avg_lead_time_days` | < 10 → "agile supply chain"; > 30 → "long-lead supply chain — planning critical" |
| finance | `currencies_used` | > 1 → "multi-currency operations — international footprint"; == 1 → "single-currency operations" |
| geography | top `region_group` revenue share | > 0.7 → "highly concentrated in {region}"; < 0.5 → "balanced multi-regional presence" |

**`overall_profile` generation:**

Build the profile string by concatenating the top insight from each detected domain.
Format: `"[Size signal]. [Channel signal]. [Production signal]. [HR signal]. [Supply chain signal]."`

Size signal: derived from `total_revenue` (< 10M → small, 10–100M → mid-size, > 100M → large)
and `total_employees` (< 50 → small team, 50–500 → mid-size, > 500 → large org).

Do not invent data — only include a segment if the underlying metric was collected.

### Markdown generation function

```python
def generate_markdown(report: dict) -> str:
    """
    Renders the report dict to a Markdown string.
    Uses only stdlib string formatting — no templating libraries.
    """
```

Structure (same as defined in `PROMPT_db_config_report_skill.md`):
- H1: Business Configuration Report + generated timestamp
- Executive Summary paragraph
- Detected Domains list
- One H2 section per domain with a metrics table and insights bullets
- Footer line with confidence and domain/table counts

### Markdown file write function

```python
def write_markdown_file(markdown: str, reports_dir: str, dry_run: bool = False) -> str | None:
    """
    Writes two files to reports_dir:
      - company_config_latest.md      (always overwritten — the canonical current report)
      - company_config_YYYYMMDD_HHMMSS.md  (timestamped archive copy)

    Deletes timestamped files beyond MAX_REPORT_FILES to avoid unbounded growth.
    Returns the path of the latest file written, or None on dry_run.
    """
    import pathlib
    import glob

    if dry_run:
        log.info("[DRY RUN] Would write .md files — skipping.")
        return None

    reports_path = pathlib.Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)

    # 1. Always-current file (overwrite)
    latest_path = reports_path / LATEST_REPORT_FILENAME
    latest_path.write_text(markdown, encoding="utf-8")
    log.info(f"Report written → {latest_path}")

    # 2. Timestamped archive copy
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = reports_path / f"company_config_{ts}.md"
    archive_path.write_text(markdown, encoding="utf-8")
    log.info(f"Archive copy  → {archive_path}")

    # 3. Prune old timestamped files (keep last MAX_REPORT_FILES)
    pattern = str(reports_path / "company_config_2*.md")  # timestamped only
    existing = sorted(glob.glob(pattern))                  # sorted = oldest first
    for old_file in existing[:-MAX_REPORT_FILES]:
        pathlib.Path(old_file).unlink(missing_ok=True)
        log.info(f"Pruned old report: {old_file}")

    return str(latest_path)
```

### Cache write function

```python
def write_snapshot(conn, report: dict, markdown: str, metrics: dict,
                   domains: list[str], duration_ms: int, errors: list[str],
                   reports_dir: str, dry_run: bool = False) -> tuple[int | None, str | None]:
    """
    Inserts a row into spine_agent.company_config_snapshots AND writes .md files.
    Returns (snapshot_id, md_file_path). Both are None on dry_run.
    Also deletes DB snapshots older than DEFAULT_KEEP_SNAPSHOTS days.
    """
    md_path = write_markdown_file(markdown, reports_dir, dry_run=dry_run)

    if dry_run:
        log.info("[DRY RUN] Would write DB snapshot — skipping INSERT.")
        return None, None

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO spine_agent.company_config_snapshots
                (collected_at, collector_version, domains_detected,
                 raw_metrics, report, markdown_summary, confidence,
                 collection_duration_ms, error_log)
            VALUES
                (NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            COLLECTOR_VERSION,
            domains,
            json.dumps(metrics),
            json.dumps(report),
            markdown,
            report["confidence"],
            duration_ms,
            json.dumps(errors),
        ))
        snapshot_id = cur.fetchone()["id"]

        # Cleanup old DB snapshots
        cur.execute("""
            DELETE FROM spine_agent.company_config_snapshots
            WHERE collected_at < NOW() - INTERVAL '%s days';
        """, (DEFAULT_KEEP_SNAPSHOTS,))

        conn.commit()
        log.info(f"DB snapshot written — id={snapshot_id}")
        return snapshot_id, md_path
```

### Cache freshness check function

```python
def is_cache_fresh(conn, max_age_hours: int = DEFAULT_CACHE_TTL_HOURS) -> bool:
    """Returns True if a recent enough snapshot already exists."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM spine_agent.latest_config_snapshot(%s) LIMIT 1;",
            (max_age_hours,)
        )
        return cur.fetchone() is not None
```

### `main()` entrypoint

```python
def main():
    parser = argparse.ArgumentParser(description="Company config periodic collector")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run queries but don't write to DB")
    parser.add_argument("--force", action="store_true",
                        help="Ignore cache age and always collect")
    parser.add_argument("--cache-ttl-hours", type=int, default=DEFAULT_CACHE_TTL_HOURS,
                        help="Skip run if snapshot newer than this exists")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_REPORTS_DIR,
                        help="Directory to write .md report files (default: reports/)")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        log.error("DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Skip if cache is fresh (unless --force)
        if not args.force and not args.dry_run:
            if is_cache_fresh(conn, args.cache_ttl_hours):
                log.info(f"Cache is fresh (< {args.cache_ttl_hours}h old). Skipping. Use --force to override.")
                return

        start = time.time()
        all_errors: list[str] = []

        with conn.cursor() as cur:
            schema_map, col_map = discover_schema(cur)

        domains = detect_domains(schema_map)
        log.info(f"Detected domains: {domains}")

        # Collect per-domain metrics
        collectors = {
            "sales":      collect_sales,
            "hr":         collect_hr,
            "production": collect_production,
            "purchasing": collect_purchasing,
            "geography":  collect_geography,
            "finance":    collect_finance,
        }

        raw_metrics: dict[str, dict] = {}
        with conn.cursor() as cur:
            for domain in domains:
                fn = collectors.get(domain)
                if fn:
                    try:
                        result = fn(cur, schema_map)
                        if result:
                            domain_errors = result.pop("errors", [])
                            all_errors.extend([f"[{domain}] {e}" for e in domain_errors])
                            raw_metrics[domain] = result
                    except Exception as e:
                        all_errors.append(f"[{domain}] Fatal: {e}")
                        log.error(f"Domain {domain} failed: {e}")

        report = assemble_report(domains, raw_metrics)
        markdown = generate_markdown(report)
        duration_ms = int((time.time() - start) * 1000)

        log.info(f"Collection complete in {duration_ms}ms — confidence={report['confidence']}")

        snapshot_id, md_path = write_snapshot(
            conn, report, markdown, raw_metrics,
            domains, duration_ms, all_errors,
            reports_dir=args.output_dir,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            print(markdown)
        else:
            log.info(f"Done. Snapshot id={snapshot_id} | Report → {md_path}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

---

## 3. Scheduler — `agent/scheduler.py`

Create or extend this file to register the collector as a scheduled job using APScheduler.

```python
"""
agent/scheduler.py

APScheduler setup for SpineAgent background jobs.
Runs independently of the main agent loop.

Usage:
    python agent/scheduler.py          # run scheduler (blocking)
    python agent/scheduler.py --once   # run all jobs once immediately and exit
"""

import os
import sys
import logging
import argparse
import subprocess
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

log = logging.getLogger("agent.scheduler")

# ── Job: company_config_collector ──────────────────────────────────────────────

COLLECTOR_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "collectors", "company_config_collector.py"
)

# Schedule: run once every 6 hours, at minute 0
COLLECTOR_CRON = CronTrigger(hour="*/6", minute=0)

# For faster iteration during development, use an interval trigger instead:
# COLLECTOR_CRON = IntervalTrigger(hours=6)


def run_company_config_collector():
    """
    Runs the collector script as a subprocess.
    Subprocess isolation ensures a collector crash doesn't kill the scheduler.
    """
    log.info("Running company_config_collector...")
    try:
        result = subprocess.run(
            [sys.executable, COLLECTOR_SCRIPT],
            capture_output=True,
            text=True,
            timeout=120,            # hard kill after 2 minutes
            env={**os.environ}      # pass through DATABASE_URL etc.
        )
        if result.returncode == 0:
            log.info("company_config_collector completed successfully.")
        else:
            log.error(
                f"company_config_collector exited with code {result.returncode}.\n"
                f"STDERR: {result.stderr[:500]}"
            )
    except subprocess.TimeoutExpired:
        log.error("company_config_collector timed out after 120s.")
    except Exception as e:
        log.error(f"company_config_collector failed to launch: {e}")


# ── Scheduler factory ───────────────────────────────────────────────────────────

def build_scheduler(blocking: bool = True):
    """
    Returns a configured APScheduler instance with all jobs registered.
    blocking=True  → BlockingScheduler (for standalone use)
    blocking=False → BackgroundScheduler (for embedding in FastAPI/async app)
    """
    SchedulerClass = BlockingScheduler if blocking else BackgroundScheduler
    scheduler = SchedulerClass(timezone="UTC")

    scheduler.add_job(
        run_company_config_collector,
        trigger=COLLECTOR_CRON,
        id="company_config_collector",
        name="Business Configuration Collector",
        replace_existing=True,
        misfire_grace_time=300,     # allow up to 5min late start before skipping
        coalesce=True,              # if multiple firings were missed, run only once
    )

    return scheduler


# ── CLI entrypoint ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SpineAgent background scheduler")
    parser.add_argument("--once", action="store_true",
                        help="Run all jobs once immediately and exit")
    args = parser.parse_args()

    if args.once:
        log.info("--once flag: running all jobs immediately.")
        run_company_config_collector()
        return

    scheduler = build_scheduler(blocking=True)
    log.info("Scheduler started. Press Ctrl+C to stop.")

    # Run the collector immediately on startup (don't wait for first cron tick)
    scheduler.add_job(
        run_company_config_collector,
        trigger="date",
        run_date=datetime.utcnow(),
        id="company_config_collector_startup",
        name="Business Configuration Collector (startup)"
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
```

---

## 4. Modify the Skill — `skills/builtin/analyze_company_config/code.py`

Add a **cache-read path** at the top of `execute()`. Before running any live queries,
check the `spine_agent.company_config_snapshots` table for a fresh snapshot.

The modified `execute()` flow:

```
1. Check cache (spine_agent.latest_config_snapshot(cache_ttl_hours))
   ├── Cache HIT  → return cached report + metadata (mark source="cache")
   └── Cache MISS → run live queries (original logic) + mark source="live"
                    + optionally trigger collector in background for next call
```

Add these two new inputs to `spec.yaml`:

```yaml
  - name: cache_ttl_hours
    type: integer
    required: false
    description: >
      How old (in hours) a cached snapshot can be before the skill falls back
      to live queries. Default: 6. Set to 0 to always query live.

  - name: use_cache
    type: boolean
    required: false
    description: >
      Whether to use the snapshot cache. Default: true. Set to false to force
      live queries (useful for debugging or when data just changed).
```

Add `source` to the outputs:

```yaml
  - name: source
    type: string
    description: '"cache" if the result came from spine_agent.company_config_snapshots, "live" if queried directly.'
```

Modified `execute()` skeleton (merge into the existing implementation):

```python
async def execute(self, **kwargs) -> dict:
    start = time.time()
    cache_ttl_hours = kwargs.get("cache_ttl_hours", 6)
    use_cache = kwargs.get("use_cache", True)

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    try:
        # ── Cache read ────────────────────────────────────────────────────────
        if use_cache and cache_ttl_hours > 0:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        "SELECT * FROM spine_agent.latest_config_snapshot(%s);",
                        (cache_ttl_hours,)
                    )
                    row = cur.fetchone()
                except Exception:
                    row = None  # cache table might not exist yet — fall through

            if row:
                # Resolve the latest .md path on disk (may not exist on first boot)
                import pathlib
                reports_dir = os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", "reports"
                )
                latest_md = pathlib.Path(reports_dir) / "company_config_latest.md"
                report_file = str(latest_md) if latest_md.exists() else None

                return {
                    "success": True,
                    "data": {
                        "report": row["report"],
                        "markdown_summary": row["markdown_summary"],
                        "domains_detected": list(row["domains_detected"]),
                        "source": "cache",
                        "cached_at": row["collected_at"].isoformat(),
                        "snapshot_id": row["id"],
                        "report_file": report_file,
                    },
                    "execution_ms": int((time.time() - start) * 1000)
                }

        # ── Cache miss: run live queries (original logic here) ────────────────
        # ... (keep existing schema discovery + domain analysis code) ...

        return {
            "success": True,
            "data": {
                "report": report,
                "markdown_summary": markdown_summary,
                "domains_detected": report["domains_detected"],
                "source": "live",
                "report_file": None,  # live runs don't write a file
            },
            "execution_ms": int((time.time() - start) * 1000)
        }

    finally:
        conn.close()
```

---

## 5. Docker Compose Integration

Add a `scheduler` service to `docker-compose.yml` (or `docker/docker-compose.yml`):

```yaml
  scheduler:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent   # reuse the agent Dockerfile
    command: python agent/scheduler.py
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/adventureworks
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - .:/app
```

This runs the scheduler as a long-lived sidecar alongside the main agent.

---

## 6. Optional: System Cron Alternative

If Docker is not used, provide a crontab entry the user can install manually:

```bash
# Run collector every 6 hours
# Install with: crontab -e
0 */6 * * * cd /path/to/Spine-Agent && DATABASE_URL=postgresql://... python collectors/company_config_collector.py >> /var/log/spine_collector.log 2>&1
```

Document this in a comment at the top of `company_config_collector.py`.

---

## Implementation Rules

1. **No LLM in the collector** — every insight must be generated by deterministic if/else rules in Python, not by calling Claude.
2. **Subprocess isolation** — the scheduler runs the collector as a subprocess (`subprocess.run`), never importing it directly, so a collector crash cannot take down the scheduler.
3. **Graceful degradation** — if the cache table doesn't exist yet (first boot), the skill must fall through to live queries without raising an exception.
4. **Idempotent** — running the collector twice in quick succession must be safe; the freshness check prevents double inserts under normal conditions.
5. **All queries parameterized** — `%s` placeholders only, never f-strings with DB values.
6. **Imports in collector:** `psycopg2`, `psycopg2.extras`, `os`, `sys`, `json`, `time`, `logging`, `argparse`, `traceback`, `datetime`, `pathlib`, `glob`, `subprocess` — nothing else.
7. **Imports in scheduler:** `apscheduler`, `os`, `sys`, `logging`, `argparse`, `subprocess`, `datetime`.
8. **Migration file** must be idempotent — use `CREATE TABLE IF NOT EXISTS` and `CREATE OR REPLACE FUNCTION`.
9. **`reports/` directory** must be created automatically by the collector (`mkdir parents=True, exist_ok=True`) — never assume it exists.
10. **`company_config_latest.md` is always overwritten** on each successful run; timestamped copies are pruned to the last `MAX_REPORT_FILES` files.

---

## File Locations Summary

| Artifact | Path |
|---|---|
| Cache table migration | `db/migrations/002_company_config_cache.sql` |
| Collector script | `collectors/company_config_collector.py` |
| Scheduler | `agent/scheduler.py` |
| Modified skill | `skills/builtin/analyze_company_config/code.py` |
| Current report (always overwritten) | `reports/company_config_latest.md` |
| Timestamped archive copies | `reports/company_config_YYYYMMDD_HHMMSS.md` (last 7 kept) |
| Original skill prompt | `PROMPT_db_config_report_skill.md` |
| Skill schema reference | `SKILL_SCHEMA_AND_REGISTRY.md` |
| Docker Compose | `docker-compose.yml` or `docker/docker-compose.yml` |

---

## Expected Behavior After Implementation

| Scenario | Result |
|---|---|
| First boot — no snapshot exists | Skill runs live queries, returns `source: "live"`, `report_file: null` |
| Snapshot < 6h old | Skill reads DB cache, returns `source: "cache"`, `report_file: "reports/company_config_latest.md"` |
| Snapshot > 6h old | Skill runs live queries; collector refreshes cache + `.md` on next cron tick |
| `use_cache=false` | Always runs live queries regardless of cache/file state |
| Collector crashes | DB cache + `.md` stay at last good state; skill falls back to live queries |
| Collector runs `--dry-run` | Prints Markdown to stdout; writes nothing to DB or disk |
| Collector runs `--force` | Ignores freshness check; overwrites DB snapshot and `reports/company_config_latest.md` |
| Collector runs `--output-dir /tmp` | Writes `.md` files to `/tmp/` instead of `reports/` |
