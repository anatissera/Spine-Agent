# Prompt: Generate `analyze_company_config` Skill for SpineAgent

## Context

This is a SpineAgent project (see `SKILL_SCHEMA_AND_REGISTRY.md` for the skill contract).
You need to implement a new skill that introspects any company PostgreSQL database and
produces a structured **Business Configuration Report** — a plain-language description of
how the company is operationally set up, derived entirely from the database schema and data.

The target database resembles AdventureWorks-for-Postgres in structure but may only contain
a subset of those tables. The skill must be resilient to missing tables/schemas.

---

## Objective

Create the skill `analyze_company_config` as three files inside
`skills/builtin/analyze_company_config/`:

```
skills/builtin/analyze_company_config/
├── spec.yaml
├── code.py
└── metadata.json
```

---

## Skill Specification

### `spec.yaml`

```yaml
name: analyze_company_config
description: >
  Introspects the connected PostgreSQL database to produce a structured
  Business Configuration Report that describes how the company is operationally
  set up: its org structure, product catalog, sales process, inventory policy,
  purchasing relationships, manufacturing capacity, and geographic reach —
  all derived from live schema and data.

classification: READ

trigger:
  modes: [assist, act]
  intent_signals:
    - "how is the company configured"
    - "company operational setup"
    - "business configuration report"
    - "analyze the database"
    - "how does this company work"
    - "organizational structure from database"

inputs:
  - name: schemas
    type: list[str]
    required: false
    description: >
      List of PostgreSQL schema names to inspect.
      Defaults to all non-system schemas if omitted.
  - name: sample_rows
    type: integer
    required: false
    description: >
      Number of sample rows to pull per table for data-driven insights.
      Defaults to 100. Lower values = faster but less accurate.

outputs:
  - name: report
    type: object
    description: >
      Structured report with sections for each business domain found.
      Each section contains findings (str), key_metrics (dict), and
      configuration_insights (list[str]).
  - name: markdown_summary
    type: string
    description: Human-readable Markdown version of the report.
  - name: domains_detected
    type: list[str]
    description: Which business domains were found (e.g. sales, hr, production).

dependencies:
  - type: database
    name: company_db
    connection_env: "DATABASE_URL"

domain: cross-domain
trigger_type: on_demand

constraints:
  max_execution_time_ms: 30000
  requires_approval: false
  safe_to_retry: true
```

---

### `code.py`

The class must inherit from `BaseSkill` and implement `async def execute(self, **kwargs) -> dict`.

**What the code must do — section by section:**

#### 0. Schema Discovery
- Query `information_schema.tables` to list all user-defined schemas and tables.
- Filter to the schemas requested (or all non-system schemas if not provided).
- Build a map: `{schema_name: [table_name, ...]}`.
- For each table, also query `information_schema.columns` to get column names and types.
- Use this map throughout — never hardcode table names; always check presence first.

#### 1. Domain Detection
Detect which business domains are present by looking for characteristic tables.
Use this mapping (check by schema name prefix OR table name):

| Domain Key | Indicator tables (any of these suffices) |
|---|---|
| `sales` | `sales.salesorderheader`, `sales.customer`, `sales.salesperson` |
| `hr` | `humanresources.employee`, `humanresources.department` |
| `production` | `production.product`, `production.workorder`, `production.productinventory` |
| `purchasing` | `purchasing.vendor`, `purchasing.purchaseorderheader` |
| `person` | `person.person`, `person.address` |
| `finance` | any table with columns named `taxamt`, `freight`, `currencycode`, `subtotal` |
| `geography` | `person.stateprovince`, `sales.salesterritory`, `person.countryregion` |

Store detected domains in a list. Only analyze detected domains.

#### 2. Per-Domain Analysis

For each detected domain, run the relevant queries below.
All queries must use parameterized form (`%s`) — never f-strings with variable input.
Wrap each query in a try/except so a missing table never crashes the skill.

---

**SALES domain** — run if `sales.salesorderheader` exists:

```sql
-- Volume and revenue overview
SELECT
  COUNT(*) AS total_orders,
  MIN(orderdate) AS first_order_date,
  MAX(orderdate) AS last_order_date,
  ROUND(AVG(subtotal)::numeric, 2) AS avg_order_value,
  ROUND(SUM(subtotal)::numeric, 2) AS total_revenue,
  COUNT(DISTINCT customerid) AS unique_customers
FROM sales.salesorderheader;

-- Order status distribution
SELECT status, COUNT(*) AS count
FROM sales.salesorderheader
GROUP BY status ORDER BY count DESC;

-- Online vs offline split
SELECT onlineorderflag, COUNT(*) AS count
FROM sales.salesorderheader
GROUP BY onlineorderflag;

-- Top sales territories (if sales.salesterritory exists)
SELECT t.name, COUNT(o.salesorderid) AS orders, ROUND(SUM(o.subtotal)::numeric,2) AS revenue
FROM sales.salesorderheader o
JOIN sales.salesterritory t ON o.territoryid = t.territoryid
GROUP BY t.name ORDER BY revenue DESC LIMIT 5;

-- Special offers active (if sales.specialoffer exists)
SELECT COUNT(*) AS active_offers, ROUND(AVG(discountpct)::numeric*100, 1) AS avg_discount_pct
FROM sales.specialoffer
WHERE getdate() BETWEEN startdate AND enddate;
```

Extract insights like:
- Total lifetime revenue, order volume, date range of operations.
- Average order value → price tier (budget/mid/premium).
- Online vs in-store ratio → channel mix.
- Top territories → geographic concentration.
- Discount strategy (if specialoffer table exists).

---

**HR domain** — run if `humanresources.employee` exists:

```sql
-- Headcount and seniority
SELECT
  COUNT(*) AS total_employees,
  COUNT(*) FILTER (WHERE currentflag = true) AS active_employees,
  COUNT(*) FILTER (WHERE salariedflag = true) AS salaried,
  COUNT(*) FILTER (WHERE salariedflag = false) AS hourly,
  ROUND(AVG(EXTRACT(YEAR FROM AGE(CURRENT_DATE, hiredate))), 1) AS avg_tenure_years
FROM humanresources.employee;

-- Department distribution
SELECT d.name AS department, d.groupname, COUNT(edh.businessentityid) AS headcount
FROM humanresources.employeedepartmenthistory edh
JOIN humanresources.department d ON edh.departmentid = d.departmentid
WHERE edh.enddate IS NULL
GROUP BY d.name, d.groupname ORDER BY headcount DESC;

-- Pay range (if employeepayhistory exists)
SELECT
  ROUND(MIN(rate)::numeric, 2) AS min_rate,
  ROUND(MAX(rate)::numeric, 2) AS max_rate,
  ROUND(AVG(rate)::numeric, 2) AS avg_rate
FROM humanresources.employeepayhistory eph
WHERE ratechangedate = (
  SELECT MAX(ratechangedate)
  FROM humanresources.employeepayhistory eph2
  WHERE eph2.businessentityid = eph.businessentityid
);
```

Extract insights like:
- Total vs active employees, employment type mix.
- Department breakdown → organizational structure (manufacturing-heavy vs sales-heavy).
- Pay range → compensation strategy signal.

---

**PRODUCTION domain** — run if `production.product` exists:

```sql
-- Catalog overview
SELECT
  COUNT(*) AS total_products,
  COUNT(*) FILTER (WHERE finishedgoodsflag = true) AS sellable_products,
  COUNT(*) FILTER (WHERE makeflag = true) AS manufactured_inhouse,
  COUNT(DISTINCT productsubcategoryid) AS subcategories,
  ROUND(AVG(listprice)::numeric, 2) AS avg_list_price,
  ROUND(AVG(standardcost)::numeric, 2) AS avg_standard_cost
FROM production.product
WHERE sellenddate IS NULL OR sellenddate > CURRENT_DATE;

-- Category breakdown
SELECT pc.name AS category, COUNT(p.productid) AS products
FROM production.product p
JOIN production.productsubcategory ps ON p.productsubcategoryid = ps.productsubcategoryid
JOIN production.productcategory pc ON ps.productcategoryid = pc.productcategoryid
GROUP BY pc.name ORDER BY products DESC;

-- Inventory health (if productinventory exists)
SELECT
  COUNT(DISTINCT p.productid) AS products_tracked,
  SUM(pi.quantity) AS total_units_on_hand,
  COUNT(*) FILTER (WHERE pi.quantity <= p.reorderpoint) AS products_at_reorder
FROM production.productinventory pi
JOIN production.product p ON pi.productid = p.productid;

-- Manufacturing complexity (if workorder exists)
SELECT
  COUNT(DISTINCT workorderid) AS total_workorders,
  ROUND(AVG(orderqty)::numeric, 1) AS avg_batch_size,
  COUNT(*) FILTER (WHERE enddate < duedate) AS on_time_completions
FROM production.workorder;
```

Extract insights like:
- Make vs buy ratio (manufactured_inhouse vs purchased).
- Product catalog depth and category structure.
- Inventory health: % of products at or below reorder point.
- Manufacturing capacity signal from work order volume.

---

**PURCHASING domain** — run if `purchasing.vendor` exists:

```sql
-- Vendor base
SELECT
  COUNT(*) AS total_vendors,
  COUNT(*) FILTER (WHERE activeflag = true) AS active_vendors,
  COUNT(*) FILTER (WHERE preferredvendorstatus = true) AS preferred_vendors,
  ROUND(AVG(creditrating)::numeric, 2) AS avg_credit_rating
FROM purchasing.vendor;

-- Purchase order volume (if purchaseorderheader exists)
SELECT
  COUNT(*) AS total_purchase_orders,
  ROUND(SUM(subtotal)::numeric, 2) AS total_spend,
  ROUND(AVG(subtotal)::numeric, 2) AS avg_po_value,
  MIN(orderdate) AS first_po_date,
  MAX(orderdate) AS last_po_date
FROM purchasing.purchaseorderheader;

-- Lead time (if productvendor exists)
SELECT
  ROUND(AVG(averageleadtime)::numeric, 1) AS avg_lead_time_days,
  MIN(averageleadtime) AS min_lead_time,
  MAX(averageleadtime) AS max_lead_time
FROM purchasing.productvendor
WHERE averageleadtime IS NOT NULL;
```

Extract insights like:
- Vendor count and quality (credit rating, preferred ratio).
- Total procurement spend and average PO size.
- Supply chain lead time → operational agility signal.

---

**GEOGRAPHY domain** — run if `sales.salesterritory` exists:

```sql
SELECT
  t.group AS region_group,
  COUNT(DISTINCT t.territoryid) AS territories,
  COUNT(DISTINCT o.salesorderid) AS orders,
  ROUND(SUM(o.subtotal)::numeric, 2) AS revenue
FROM sales.salesterritory t
LEFT JOIN sales.salesorderheader o ON t.territoryid = o.territoryid
GROUP BY t.group ORDER BY revenue DESC NULLS LAST;
```

Extract insights like:
- Geographic footprint (regions, countries).
- Revenue concentration by region → market focus.

---

**FINANCE domain** — detect by column names across tables:

```sql
-- Currency usage (if sales.currency and currencyrate exist)
SELECT COUNT(DISTINCT currencycode) AS currencies_used
FROM sales.currencyrate;

-- Tax configuration (if salestaxrate exists)
SELECT COUNT(DISTINCT stateprovinceid) AS tax_jurisdictions,
       ROUND(AVG(taxrate)::numeric, 2) AS avg_tax_rate
FROM sales.salestaxrate;
```

Extract insights like:
- Multi-currency → international operations.
- Tax jurisdictions → regulatory complexity.

---

#### 3. Report Assembly

After all domain queries complete, assemble the final report structure:

```python
report = {
    "generated_at": datetime.utcnow().isoformat(),
    "domains_detected": [...],  # list of domain keys found
    "sections": {
        "sales": {
            "findings": "...",               # 2-3 sentence human summary
            "key_metrics": {...},            # dict of metric_name: value
            "configuration_insights": [...]  # list of plain-language bullets
        },
        "hr": { ... },
        "production": { ... },
        "purchasing": { ... },
        "geography": { ... },
        "finance": { ... }
    },
    "overall_profile": "...",  # 1 paragraph executive summary
    "confidence": "high|medium|low"  # based on how many tables were found
}
```

**`findings` example for sales:**
> "The company has processed 31,465 orders since 2001, generating $109M in total revenue with an average order value of $3,457. Sales are split 73% online and 27% in-store, concentrated in North America (Southwest territory leading at $21M)."

**`configuration_insights` example for production:**
> - "67% of products are manufactured in-house, indicating significant vertical integration."
> - "12% of SKUs are currently at or below reorder point — potential stockout risk."
> - "Average batch size of 8.3 units suggests small-batch / custom manufacturing model."

**`overall_profile` example:**
> "This appears to be a mid-size B2C/B2B hybrid manufacturer with $109M in lifetime revenue, strong North American focus, and deep vertical integration in production. The company operates through both direct online channels and a regional sales force of ~17 reps. Supply chain is moderately concentrated with 104 active vendors and an average lead time of 16 days."

**Confidence scoring:**
- `high`: 4+ domains detected with core tables present
- `medium`: 2–3 domains detected
- `low`: only 1 domain or fewer than 5 tables total

#### 4. Markdown Generation

Generate `markdown_summary` as a formatted Markdown string:

```markdown
# Business Configuration Report
_Generated: {generated_at}_

## Executive Summary
{overall_profile}

## Detected Domains
{comma-separated list}

## Sales & Revenue
**Key Metrics**
| Metric | Value |
|---|---|
| Total Orders | ... |
| ... | ... |

**Insights**
- ...

## Human Resources & Organization
...

## Product & Production
...

## Purchasing & Supply Chain
...

## Geographic Footprint
...

## Financial Configuration
...

---
_Confidence: {confidence} — based on {N} domains detected across {M} tables._
```

#### 5. Return Value

```python
return {
    "success": True,
    "data": {
        "report": report,
        "markdown_summary": markdown_summary,
        "domains_detected": report["domains_detected"]
    },
    "execution_ms": int((time.time() - start) * 1000)
}
```

---

### `metadata.json`

```json
{
  "skill_name": "analyze_company_config",
  "created_at": "2026-04-14T00:00:00Z",
  "author": "human",
  "version": "1.0.0",
  "usage": {
    "total_invocations": 0,
    "last_invoked": null,
    "success_rate": 1.0,
    "avg_execution_ms": 0
  },
  "health": "ok",
  "tags": ["cross-domain", "reporting", "configuration", "introspection", "read"]
}
```

---

## Implementation Rules

1. **Never hardcode** table names — always check `information_schema.tables` first.
2. **Wrap every query** in try/except; log the table/query that failed but continue.
3. **Parameterized queries only** — use `%s` placeholders with psycopg2, never f-strings with data.
4. **No external calls** — no HTTP, no Claude API calls, no subprocess. Pure DB + Python.
5. **Imports allowed:** `psycopg2`, `os`, `time`, `asyncio`, `datetime`, `json`, `collections`.
6. **Connection:** read from `os.environ["DATABASE_URL"]`; use connection pooling with `with conn.cursor() as cur`.
7. **Timeout:** total execution must complete within 25 seconds; add a global start-time check.
8. **Missing domain = omit section** — don't include an empty section in the report.
9. **Confidence must be computed** from the number of domains found, not hardcoded.
10. Inherit from `skills.base_skill.BaseSkill` and implement `async def execute(self, **kwargs) -> dict`.

---

## Test Inputs

When testing, use these realistic values:

```python
# Full run — discover all schemas automatically
result = await skill.execute()

# Scoped run — only inspect sales + humanresources
result = await skill.execute(schemas=["sales", "humanresources"])

# Fast run with smaller sample
result = await skill.execute(sample_rows=10)
```

Expected `domains_detected` for a full AdventureWorks DB:
`["sales", "hr", "production", "purchasing", "person", "geography", "finance"]`

---

## File Locations

| File | Path |
|---|---|
| Base class | `skills/base_skill.py` |
| Skill registry | `skills/registry.py` |
| Example seed skill | `skills/builtin/query_order_status/` |
| Skill schema reference | `SKILL_SCHEMA_AND_REGISTRY.md` |
| Database URL env var | `DATABASE_URL` in `.env` |
