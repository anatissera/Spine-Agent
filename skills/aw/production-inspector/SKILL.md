---
name: production-inspector
description: >
  Use this skill when asked about production, work orders, inventory, scrap,
  or manufacturing: "what work orders are open for product X?", "show me the
  scrap rate for this product", "is there enough inventory to fulfill this order?",
  "what is the production schedule for work order #Y?", "trace the transaction
  history for product Z", "which products have the highest scrap?", or any
  question about the production domain. This is the Production domain view of
  the operational spine.
metadata:
  tools:
    - run_sql
---

# Skill: Production Inspector

## What This Skill Does

Queries the production domain — the execution layer of the operational spine.
When a sales order is placed, production creates work orders and routes them
through manufacturing. This skill tracks that process.

Produces a **production state card** for a product or work order.

Cross-domain link: `production.transactionhistory` records S/W/P events —
it is the only table that sees all three operational domains.

---

## Authorized Tables

| Table | Schema | Purpose |
|---|---|---|
| `workorder` | `production` | Work order — product, qty, scrap, dates |
| `workorderrouting` | `production` | Per-operation schedule vs. actuals |
| `transactionhistory` | `production` | Cross-domain event log (S/W/P) |
| `transactionhistoryarchive` | `production` | Archived events (2022–2024) |
| `product` | `production` | Product master — class, standard cost |
| `productinventory` | `production` | Inventory by product and location |
| `billofmaterials` | `production` | BOM — assembly depth and components |
| `scrapreason` | `production` | Scrap reason lookup (16 reasons) |
| `location` | `production` | Work center / location names |

---

## Step 1 — Resolve the Input

| Input type | Strategy |
|---|---|
| `workorderid` | Query work order directly |
| `productid` | Find all work orders for that product |
| "Scrap / quality" | Aggregate `scrappedqty / orderqty` |
| "Schedule / late" | Compare routing actuals to scheduled dates |
| "Inventory" | Query `productinventory` |
| "Trace" | Query `transactionhistory` by productid |

---

## Step 2 — Query the Work Order

```sql
-- Purpose: work order state card
SELECT
    wo.workorderid,
    wo.productid,
    p.name                                          AS product_name,
    p.class                                         AS product_class,
    wo.orderqty,
    wo.scrappedqty,
    ROUND(
        CASE WHEN wo.orderqty > 0
             THEN wo.scrappedqty::numeric / wo.orderqty * 100
             ELSE 0
        END, 2
    )                                               AS scrap_pct,
    wo.startdate,
    wo.enddate,
    wo.duedate,
    CASE
        WHEN wo.enddate IS NULL THEN 'IN PROGRESS'
        WHEN wo.enddate > wo.duedate THEN 'COMPLETED LATE'
        ELSE 'COMPLETED ON TIME'
    END                                             AS schedule_status,
    wo.scrapreasonid,
    sr.name                                         AS scrap_reason
FROM production.workorder     wo
JOIN production.product        p  ON p.productid       = wo.productid
LEFT JOIN production.scrapreason sr ON sr.scrapreasonid = wo.scrapreasonid
WHERE wo.workorderid = %s   -- or adjust for productid / date range
```

---

## Step 3 — Query Work Order Routing (schedule vs. actuals)

```sql
-- Purpose: routing schedule adherence
SELECT
    wor.workorderid,
    wor.operationsequence,
    l.name                                          AS location,
    wor.scheduledstartdate,
    wor.scheduledenddate,
    wor.actualstartdate,
    wor.actualenddate,
    wor.actualresourcehrs,
    EXTRACT(DAY FROM (wor.actualenddate - wor.scheduledenddate)) AS days_late,
    CASE
        WHEN wor.actualenddate IS NULL THEN 'IN PROGRESS'
        WHEN wor.actualenddate > wor.scheduledenddate THEN 'LATE'
        ELSE 'ON TIME'
    END                                             AS routing_status
FROM production.workorderrouting wor
JOIN production.location          l   ON l.locationid = wor.locationid
WHERE wor.workorderid = %s
ORDER BY wor.operationsequence ASC
```

---

## Step 4 — Query Transaction History (cross-domain trace)

This is the most powerful query: it traces a product's journey across Sales,
Production, and Purchasing in a single result set.

```sql
-- Purpose: cross-domain event trace for a product
SELECT
    th.transactionid,
    th.transactiondate,
    th.transactiontype,
    CASE th.transactiontype
        WHEN 'S' THEN 'Sale'
        WHEN 'W' THEN 'Work Order'
        WHEN 'P' THEN 'Purchase'
    END                                             AS domain,
    th.referenceorderid,
    th.referenceorderlineid,
    th.quantity,
    th.actualcost
FROM production.transactionhistory th
WHERE th.productid = %s
ORDER BY th.transactiondate ASC
```

To include archived events (pre-2024), UNION with the archive table:
```sql
SELECT * FROM production.transactionhistory    WHERE productid = %s
UNION ALL
SELECT * FROM production.transactionhistoryarchive WHERE productid = %s
ORDER BY transactiondate ASC
```

---

## Step 5 — Query Inventory

```sql
-- Purpose: current inventory by location
SELECT
    pi.locationid,
    l.name                                          AS location,
    pi.shelf,
    pi.bin,
    pi.quantity,
    p.name                                          AS product,
    p.standardcost,
    pi.quantity * p.standardcost                    AS inventory_value
FROM production.productinventory pi
JOIN production.product  p ON p.productid  = pi.productid
JOIN production.location l ON l.locationid = pi.locationid
WHERE pi.productid = %s
ORDER BY pi.quantity DESC
```

---

## Step 6 — Scrap Analysis (product or date range)

```sql
-- Purpose: scrap rate by product
SELECT
    p.name                                          AS product,
    p.class,
    COUNT(wo.workorderid)                           AS work_orders,
    SUM(wo.orderqty)                                AS total_ordered,
    SUM(wo.scrappedqty)                             AS total_scrapped,
    ROUND(
        SUM(wo.scrappedqty)::numeric /
        NULLIF(SUM(wo.orderqty), 0) * 100, 2
    )                                               AS scrap_pct,
    sr.name                                         AS most_common_reason
FROM production.workorder wo
JOIN production.product p ON p.productid = wo.productid
LEFT JOIN production.scrapreason sr ON sr.scrapreasonid = wo.scrapreasonid
WHERE wo.scrappedqty > 0
GROUP BY p.productid, p.name, p.class, sr.name
ORDER BY scrap_pct DESC
LIMIT 20
```

---

## Step 7 — Apply Reasoning

- **Scrap rate > 5%**: alert threshold — flag for quality investigation.
- **Routing delay**: if `actualenddate > scheduledenddate` by > 2 days, flag schedule slip.
- **No W event in transactionhistory**: a product with S events but no W events was sold but
  no work order was ever created — fulfillment gap.
- **Inventory = 0**: product sold with zero inventory on hand — potential stockout.
- **BOM depth**: `bomlevel > 2` means multi-stage assembly — higher schedule risk.

---

## Format the Production State Card

```
WORK ORDER #<id>  —  Product: <name>  [<class>]
  Status:       <IN PROGRESS / COMPLETED ON TIME / COMPLETED LATE>
  Quantities:   ordered=<n>  scrapped=<n>  (<pct>% scrap)  [reason: <name>]
  Dates:        Start <date> → Due <date> → End <date>

ROUTING  (<n> operations):
  Op <seq>  <location>  sched=<start>→<end>  actual=<start>→<end>  [LATE <n> days]

INVENTORY  (<n> locations):
  <location>  shelf=<s>  bin=<b>  qty=<n>

TRANSACTION TRACE (<n> events):
  <date>  <domain>  reforder=<id>  qty=<n>  cost=$<n>
```

---

## Constraints

- Read-only — never INSERT, UPDATE, or DELETE.
- This is the only skill authorized to query `production.*` tables.
- Always use `transactionhistory` + `transactionhistoryarchive` together for a complete trace.
- Do not infer production intent from sales data — use `workorder` directly.
