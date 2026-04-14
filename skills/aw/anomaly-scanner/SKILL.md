---
name: anomaly-scanner
description: >
  Use this skill when asked to find problems, risks, or anomalies across the
  operational spine: "what orders are at risk?", "find supply problems",
  "show me scrap spikes", "which vendors are underperforming?", "detect
  fulfillment gaps", "scan for issues", "what should I be worried about?",
  "run a health check", or any request for proactive anomaly detection across
  domains. No input required — runs a fixed set of detection queries and returns
  a ranked anomaly list. This is the detect step in the Act mode chain.
metadata:
  tools:
    - run_sql
---

# Skill: Anomaly Scanner

## What This Skill Does

Scans the operational spine for anomalies across all three domains using live
database queries. Produces a **ranked anomaly list** — each item has a severity,
entity type, entity ID, signal description, and recommended action.

This is the **detect** step. Its output feeds `order-briefing` (for deep context
on flagged entities) and `spine-monitor` (as part of the background loop).

---

## Detection Queries

Run all five checks. Collect results. Rank by severity (HIGH > MEDIUM > LOW).
Report the top 20 anomalies total.

---

### Check 1 — Supply Risk: Pending POs Past Due Date

```sql
-- Severity: HIGH
-- Signal: product ordered but not received, PO past due
SELECT
    'supply_risk'                                   AS anomaly_type,
    'HIGH'                                          AS severity,
    poh.purchaseorderid                             AS entity_id,
    'purchaseorderheader'                           AS entity_table,
    v.name                                          AS vendor,
    pod.productid,
    pod.duedate,
    pod.orderqty - pod.receivedqty                  AS outstanding_qty,
    EXTRACT(DAY FROM (NOW() - pod.duedate))::int    AS days_overdue,
    CONCAT(
        'PO #', poh.purchaseorderid,
        ' from ', v.name,
        ' is ', EXTRACT(DAY FROM (NOW() - pod.duedate))::int, ' days overdue.',
        ' Product ', pod.productid, ' — ',
        (pod.orderqty - pod.receivedqty), ' units outstanding.'
    )                                               AS signal
FROM purchasing.purchaseorderheader poh
JOIN purchasing.purchaseorderdetail pod ON pod.purchaseorderid = poh.purchaseorderid
JOIN purchasing.vendor v                ON v.businessentityid  = poh.vendorid
WHERE poh.status IN (1, 2)
  AND pod.duedate < NOW()
  AND pod.receivedqty < pod.orderqty
ORDER BY days_overdue DESC
LIMIT 10
```

---

### Check 2 — Quality Signal: High Scrap Rate Work Orders

```sql
-- Severity: MEDIUM (HIGH if scrap_pct > 20%)
-- Signal: product with abnormally high scrap rate
SELECT
    'high_scrap'                                    AS anomaly_type,
    CASE
        WHEN wo.scrappedqty::numeric / wo.orderqty > 0.20 THEN 'HIGH'
        ELSE 'MEDIUM'
    END                                             AS severity,
    wo.workorderid                                  AS entity_id,
    'workorder'                                     AS entity_table,
    NULL::varchar                                   AS vendor,
    wo.productid,
    NULL::date                                      AS duedate,
    wo.scrappedqty                                  AS outstanding_qty,
    NULL::int                                       AS days_overdue,
    CONCAT(
        'Work order #', wo.workorderid,
        ' — product ', wo.productid,
        ' scrapped ', wo.scrappedqty, '/', wo.orderqty,
        ' units (', ROUND(wo.scrappedqty::numeric / wo.orderqty * 100, 1), '%).',
        COALESCE(' Reason: ' || sr.name, '')
    )                                               AS signal
FROM production.workorder wo
LEFT JOIN production.scrapreason sr ON sr.scrapreasonid = wo.scrapreasonid
WHERE wo.orderqty > 0
  AND wo.scrappedqty::numeric / wo.orderqty > 0.05
ORDER BY wo.scrappedqty::numeric / wo.orderqty DESC
LIMIT 10
```

---

### Check 3 — Vendor Reliability: High Rejection Rate

```sql
-- Severity: MEDIUM (HIGH if rejection_pct > 15%)
-- Signal: vendor delivering defective product consistently
SELECT
    'vendor_rejection'                              AS anomaly_type,
    CASE
        WHEN SUM(pod.rejectedqty)::numeric / NULLIF(SUM(pod.receivedqty), 0) > 0.15
             THEN 'HIGH'
        ELSE 'MEDIUM'
    END                                             AS severity,
    v.businessentityid                              AS entity_id,
    'vendor'                                        AS entity_table,
    v.name                                          AS vendor,
    NULL::int                                       AS productid,
    NULL::date                                      AS duedate,
    SUM(pod.rejectedqty)::int                       AS outstanding_qty,
    NULL::int                                       AS days_overdue,
    CONCAT(
        'Vendor ', v.name,
        ' rejection rate: ',
        ROUND(SUM(pod.rejectedqty)::numeric / NULLIF(SUM(pod.receivedqty), 0) * 100, 1),
        '% (',
        SUM(pod.rejectedqty), ' rejected of ',
        SUM(pod.receivedqty), ' received).'
    )                                               AS signal
FROM purchasing.vendor v
JOIN purchasing.purchaseorderheader poh ON poh.vendorid        = v.businessentityid
JOIN purchasing.purchaseorderdetail pod ON pod.purchaseorderid = poh.purchaseorderid
WHERE pod.receivedqty > 0
GROUP BY v.businessentityid, v.name
HAVING SUM(pod.rejectedqty)::numeric / NULLIF(SUM(pod.receivedqty), 0) > 0.05
ORDER BY SUM(pod.rejectedqty)::numeric / NULLIF(SUM(pod.receivedqty), 0) DESC
LIMIT 10
```

---

### Check 4 — Fulfillment Gap: Products With Sales But No Work Orders

```sql
-- Severity: HIGH
-- Signal: product was sold (S event) but never had a work order (no W event)
-- Indicates a gap in the sales→production handoff
SELECT
    'fulfillment_gap'                               AS anomaly_type,
    'HIGH'                                          AS severity,
    s_events.productid                              AS entity_id,
    'product'                                       AS entity_table,
    NULL::varchar                                   AS vendor,
    s_events.productid,
    NULL::date                                      AS duedate,
    s_events.sale_events                            AS outstanding_qty,
    NULL::int                                       AS days_overdue,
    CONCAT(
        'Product ', s_events.productid,
        ' has ', s_events.sale_events, ' sale events',
        ' but zero work order events in transactionhistory.',
        ' Sales→Production handoff missing.'
    )                                               AS signal
FROM (
    SELECT productid, COUNT(*) AS sale_events
    FROM production.transactionhistory
    WHERE transactiontype = 'S'
    GROUP BY productid
) s_events
WHERE NOT EXISTS (
    SELECT 1 FROM production.transactionhistory w
    WHERE w.productid = s_events.productid
      AND w.transactiontype = 'W'
)
ORDER BY s_events.sale_events DESC
LIMIT 10
```

---

### Check 5 — Schedule Slip: Work Order Routing Past Scheduled End

```sql
-- Severity: MEDIUM
-- Signal: operation completed late against its routing schedule
SELECT
    'schedule_slip'                                 AS anomaly_type,
    'MEDIUM'                                        AS severity,
    wor.workorderid                                 AS entity_id,
    'workorderrouting'                              AS entity_table,
    NULL::varchar                                   AS vendor,
    wo.productid,
    wor.scheduledenddate                            AS duedate,
    EXTRACT(DAY FROM (wor.actualenddate - wor.scheduledenddate))::int AS outstanding_qty,
    EXTRACT(DAY FROM (wor.actualenddate - wor.scheduledenddate))::int AS days_overdue,
    CONCAT(
        'Work order #', wor.workorderid,
        ' op ', wor.operationsequence,
        ' at ', l.name,
        ' completed ', EXTRACT(DAY FROM (wor.actualenddate - wor.scheduledenddate))::int,
        ' days late.'
    )                                               AS signal
FROM production.workorderrouting wor
JOIN production.workorder wo ON wo.workorderid = wor.workorderid
JOIN production.location   l  ON l.locationid  = wor.locationid
WHERE wor.actualenddate IS NOT NULL
  AND wor.actualenddate > wor.scheduledenddate
  AND EXTRACT(DAY FROM (wor.actualenddate - wor.scheduledenddate)) > 2
ORDER BY days_overdue DESC
LIMIT 10
```

---

## Synthesis Step

After running all five checks:

1. Collect all anomalies into a single list.
2. Sort by severity (HIGH first), then by `days_overdue` or `outstanding_qty` descending.
3. Deduplicate if the same entity appears in multiple checks (keep highest severity).
4. Output the ranked list.

---

## Output Format

```
ANOMALY SCAN RESULTS  — <timestamp>
========================================
Found <N> anomalies  |  HIGH: <n>  MEDIUM: <n>  LOW: <n>

[HIGH]  supply_risk        PO #<id>   <signal>
[HIGH]  fulfillment_gap    product <id>  <signal>
[MEDIUM] high_scrap        WO #<id>   <signal>
[MEDIUM] vendor_rejection  vendor <id>  <signal>
[MEDIUM] schedule_slip     WO #<id>   <signal>
...

RECOMMENDED NEXT STEP:
  Run `order-briefing` on the top <n> HIGH anomalies for full cross-domain context.
```

---

## Thresholds Reference

| Check | MEDIUM threshold | HIGH threshold |
|---|---|---|
| Supply overdue | any | any past due |
| Scrap rate | > 5% | > 20% |
| Vendor rejection | > 5% | > 15% |
| Fulfillment gap | any S without W | — |
| Schedule slip | > 2 days | — |

---

## Constraints

- Read-only — never INSERT, UPDATE, or DELETE.
- Always run all five checks before synthesizing — do not skip checks.
- Do not invent thresholds beyond those listed above.
- The output list is the input to `order-briefing` — keep entity_id values accurate.
