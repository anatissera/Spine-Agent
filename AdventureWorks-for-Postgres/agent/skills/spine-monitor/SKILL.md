---
name: spine-monitor
description: >
  Use this skill when asked to run a background health check, monitor the
  operational spine, or generate a proactive status report: "check the spine",
  "run the monitor", "what is the operational health right now?", "generate
  a daily health report", "are there any issues I should know about?",
  "monitor the database", or any request for a proactive, unprompted scan of
  the full system state. This is the Monitor mode entry point — it runs without
  a specific user question and produces a structured health report with alerts.
metadata:
  tools:
    - run_sql
---

# Skill: Spine Monitor

## What This Skill Does

Runs a fixed set of live health checks against the operational spine and
produces a **structured health report** with severity-ranked alerts. Designed
to run in background (Monitor mode) without a specific user question.

The human is not in the loop during detection — only at the approval step
after the report is produced.

---

## The Two Live Anchors

From `wiki/spine.md`:
> "Live monitoring must use `purchaseorderheader` (status 1–4) and
> `workorderrouting` (schedule vs. actuals)."

All 31,465 sales orders are terminal (status=5). Monitor mode operates on:
1. `purchasing.purchaseorderheader` — the only active state machine
2. `production.workorderrouting` — schedule vs. actuals
3. `production.transactionhistory` — cross-domain event coherence

---

## Health Checks (run in sequence)

### Check 1 — Purchasing State Machine Snapshot

The pulse of the system: how many POs are in each live state right now.

```sql
-- Purpose: purchasing state machine snapshot
SELECT
    status,
    CASE status
        WHEN 1 THEN 'Pending'
        WHEN 2 THEN 'Approved'
        WHEN 3 THEN 'Rejected'
        WHEN 4 THEN 'Complete'
    END                                         AS status_label,
    COUNT(*)                                    AS po_count,
    SUM(subtotal + taxamt + freight)            AS total_value
FROM purchasing.purchaseorderheader
GROUP BY status
ORDER BY status
```

Flag: `Pending (status=1) > 50` or `Rejected (status=3) > 20` in current period.

---

### Check 2 — Active Supply Risk (Pending POs Past Due)

```sql
-- Purpose: pending POs with overdue line items
SELECT
    COUNT(DISTINCT poh.purchaseorderid)         AS overdue_pos,
    COUNT(DISTINCT pod.productid)               AS affected_products,
    SUM(pod.orderqty - pod.receivedqty)         AS total_outstanding_units,
    MAX(EXTRACT(DAY FROM (NOW() - pod.duedate))::int) AS max_days_overdue,
    AVG(EXTRACT(DAY FROM (NOW() - pod.duedate))::float)::numeric(10,1) AS avg_days_overdue
FROM purchasing.purchaseorderheader poh
JOIN purchasing.purchaseorderdetail pod ON pod.purchaseorderid = poh.purchaseorderid
WHERE poh.status IN (1, 2)
  AND pod.duedate < NOW()
  AND pod.receivedqty < pod.orderqty
```

Flag: `overdue_pos > 0` → HIGH alert. Include max and avg days overdue.

---

### Check 3 — Production Schedule Adherence

```sql
-- Purpose: work order routing schedule adherence summary
SELECT
    COUNT(*)                                    AS total_routed_ops,
    SUM(CASE WHEN wor.actualenddate IS NULL THEN 1 ELSE 0 END) AS in_progress,
    SUM(CASE WHEN wor.actualenddate > wor.scheduledenddate THEN 1 ELSE 0 END) AS completed_late,
    SUM(CASE WHEN wor.actualenddate <= wor.scheduledenddate THEN 1 ELSE 0 END) AS completed_on_time,
    ROUND(
        SUM(CASE WHEN wor.actualenddate > wor.scheduledenddate THEN 1 ELSE 0 END)::numeric /
        NULLIF(SUM(CASE WHEN wor.actualenddate IS NOT NULL THEN 1 ELSE 0 END), 0) * 100,
        1
    )                                           AS late_completion_pct,
    MAX(EXTRACT(DAY FROM (wor.actualenddate - wor.scheduledenddate))::int) AS worst_slip_days
FROM production.workorderrouting wor
```

Flag: `late_completion_pct > 15%` → MEDIUM; `worst_slip_days > 14` → HIGH.

---

### Check 4 — Scrap Rate Overview

```sql
-- Purpose: current scrap rate across all work orders
SELECT
    COUNT(*)                                    AS total_work_orders,
    SUM(CASE WHEN scrappedqty > 0 THEN 1 ELSE 0 END) AS orders_with_scrap,
    SUM(orderqty)                               AS total_ordered,
    SUM(scrappedqty)                            AS total_scrapped,
    ROUND(
        SUM(scrappedqty)::numeric / NULLIF(SUM(orderqty), 0) * 100, 2
    )                                           AS overall_scrap_pct,
    MAX(
        CASE WHEN orderqty > 0
             THEN ROUND(scrappedqty::numeric / orderqty * 100, 1)
             ELSE 0
        END
    )                                           AS max_single_wo_scrap_pct
FROM production.workorder
```

Flag: `overall_scrap_pct > 2%` → MEDIUM; `max_single_wo_scrap_pct > 20%` → HIGH.

---

### Check 5 — Cross-Domain Event Coherence

```sql
-- Purpose: detect products with sales events but no production or purchasing events
-- These are fulfillment gaps — sold but never made or sourced
SELECT
    COUNT(DISTINCT s.productid)                 AS products_sold,
    COUNT(DISTINCT w.productid)                 AS products_with_workorders,
    COUNT(DISTINCT p.productid)                 AS products_with_purchases,
    COUNT(DISTINCT s.productid) -
        COUNT(DISTINCT w.productid)             AS products_sold_not_produced,
    COUNT(DISTINCT s.productid) -
        COUNT(DISTINCT p.productid)             AS products_sold_not_purchased
FROM (SELECT DISTINCT productid FROM production.transactionhistory WHERE transactiontype = 'S') s
LEFT JOIN (SELECT DISTINCT productid FROM production.transactionhistory WHERE transactiontype = 'W') w
    ON w.productid = s.productid
LEFT JOIN (SELECT DISTINCT productid FROM production.transactionhistory WHERE transactiontype = 'P') p
    ON p.productid = s.productid
```

Flag: `products_sold_not_produced > 0` → HIGH (fulfillment gap).

---

### Check 6 — Vendor Quality Overview

```sql
-- Purpose: top vendors by rejection rate
SELECT
    v.name                                      AS vendor,
    SUM(pod.receivedqty)                        AS received,
    SUM(pod.rejectedqty)                        AS rejected,
    ROUND(
        SUM(pod.rejectedqty)::numeric / NULLIF(SUM(pod.receivedqty), 0) * 100, 1
    )                                           AS rejection_pct
FROM purchasing.vendor v
JOIN purchasing.purchaseorderheader poh ON poh.vendorid        = v.businessentityid
JOIN purchasing.purchaseorderdetail pod ON pod.purchaseorderid = poh.purchaseorderid
WHERE pod.receivedqty > 0
GROUP BY v.businessentityid, v.name
HAVING SUM(pod.rejectedqty)::numeric / NULLIF(SUM(pod.receivedqty), 0) > 0.05
ORDER BY rejection_pct DESC
LIMIT 5
```

Flag: any vendor > 5% → MEDIUM; any vendor > 15% → HIGH.

---

## Alert Classification

After running all checks, classify each result:

| Severity | Meaning | Recommended action |
|---|---|---|
| HIGH | Immediate operational risk — revenue or delivery impact | Escalate; run `order-briefing` on affected entities |
| MEDIUM | Quality or efficiency degradation | Monitor; investigate on next cycle |
| LOW | Informational — within normal bounds | Log only |

---

## Output Format

```
╔══════════════════════════════════════════════════════════╗
║  SPINE HEALTH REPORT  —  <timestamp>                     ║
╚══════════════════════════════════════════════════════════╝

OVERALL STATUS:  <HEALTHY / DEGRADED / AT RISK>
Alerts:  HIGH=<n>  MEDIUM=<n>  LOW=<n>

──────────────────────────────────────────────────────────
1. PURCHASING STATE MACHINE
   Pending: <n>  |  Approved: <n>  |  Rejected: <n>  |  Complete: <n>
   [HIGH]  <n> POs overdue — max <n> days  avg <n> days
   [LOW]   Purchasing pipeline healthy
   Total open value: $<amount>

2. PRODUCTION SCHEDULE
   <n> operations total  |  <n> in progress  |  <pct>% completed late
   [HIGH]   Worst slip: <n> days on WO #<id>
   [MEDIUM] Late completion rate <pct>% exceeds 15% threshold

3. QUALITY / SCRAP
   Overall scrap rate: <pct>%  (<n> units scrapped of <n> ordered)
   [HIGH]   WO #<id> — <pct>% scrap  (<reason>)
   [LOW]    Scrap within normal bounds

4. FULFILLMENT COHERENCE
   Products sold: <n>  |  With work orders: <n>  |  With purchases: <n>
   [HIGH]   <n> products sold but never produced
   [LOW]    Event chain coherent

5. VENDOR QUALITY
   Vendors above 5% rejection threshold: <n>
   [HIGH]   <vendor>: <pct>% rejection rate
   [MEDIUM] <vendor>: <pct>% rejection rate

──────────────────────────────────────────────────────────
ACTIONS REQUIRED:
  1. Run `order-briefing` on <N> HIGH-severity entities
  2. <specific action>
```

---

## Decision Rules for Overall Status

- **AT RISK**: any HIGH alert exists
- **DEGRADED**: no HIGH alerts, but 2+ MEDIUM alerts
- **HEALTHY**: 0 HIGH, 0–1 MEDIUM

---

## Constraints

- Read-only — never INSERT, UPDATE, or DELETE.
- Always run all six checks — do not skip checks even if earlier ones fire alerts.
- Timestamp the report header with the actual query execution time.
- If overall status is AT RISK, always recommend `order-briefing` on the
  specific HIGH entities as the immediate next step.
- This skill does not itself call `anomaly-scanner` — it runs its own
  summary-level checks. For entity-level detail, route to `order-briefing`.
