---
name: order-briefing
description: >
  Use this skill when asked for a complete, cross-domain brief on one or more
  orders or products: "give me the full picture on order #X", "brief me on the
  top at-risk orders", "what is the cross-domain status of product Y?", "prepare
  an operational brief for this week's flagged orders", or any request that
  requires synthesizing the sales, production, and purchasing views of the same
  entity into a single coherent document. This skill chains order-inspector,
  production-inspector, and vendor-inspector. It is the Act mode composition
  skill — its output is ready for human review or escalation.
metadata:
  tools:
    - run_sql
---

# Skill: Order Briefing

## What This Skill Does

Produces a **complete cross-domain operational brief** by sequencing the three
domain inspector queries — Sales, Production, Purchasing — over the same spine
object (order or product) and synthesizing them into a single document.

This is the composition skill. The human is displaced from the relay (gathering
data from three systems) and placed at the approval step (reviewing the brief).

---

## When to Activate

- User asks for a "full picture", "brief", or "cross-domain status" of an order or product.
- `anomaly-scanner` output lists HIGH anomalies → run this skill on each.
- `spine-monitor` fires an alert → run this skill on the flagged entities.

---

## Input Resolution

Determine what the user is asking about:

| Input | Entry point |
|---|---|
| `salesorderid` | Start with Step 1 (Sales view), derive products, then proceed |
| `productid` | Start with Step 2 (Production view), cross-reference purchasing |
| `purchaseorderid` | Start with Step 3 (Purchasing view), cross-reference product |
| Anomaly list from scanner | Process each entity by its `entity_table` type |
| "Top N at risk" | Run `anomaly-scanner` first, then brief the top N HIGH items |

---

## Step 1 — Sales Domain View

Run the order header query:

```sql
SELECT
    soh.salesorderid,
    soh.orderdate,
    soh.duedate,
    soh.shipdate,
    CASE soh.status
        WHEN 1 THEN 'In Process' WHEN 2 THEN 'Approved'
        WHEN 3 THEN 'Backordered' WHEN 4 THEN 'Rejected'
        WHEN 5 THEN 'Shipped'
    END                                         AS status_label,
    CASE WHEN soh.onlineorderflag THEN 'Online' ELSE 'B2B' END AS channel,
    soh.totaldue,
    st.name                                     AS territory,
    st."group"                                  AS region,
    CASE WHEN soh.shipdate > soh.duedate THEN 'LATE' ELSE 'ON TIME' END AS sla_status,
    EXTRACT(DAY FROM (soh.shipdate - soh.orderdate)) AS cycle_days
FROM sales.salesorderheader soh
JOIN sales.salesterritory st ON st.territoryid = soh.territoryid
WHERE soh.salesorderid = %s
```

Then get the product IDs from this order — they are the cross-domain anchors:

```sql
SELECT productid, orderqty, unitprice, linetotal
FROM sales.salesorderdetail
WHERE salesorderid = %s
ORDER BY linetotal DESC
```

---

## Step 2 — Production Domain View

For each `productid` from Step 1 (or if entering from a productid directly):

```sql
SELECT
    wo.workorderid,
    wo.productid,
    p.name                                      AS product_name,
    p.class,
    wo.orderqty,
    wo.scrappedqty,
    ROUND(wo.scrappedqty::numeric / NULLIF(wo.orderqty, 0) * 100, 1) AS scrap_pct,
    wo.startdate,
    wo.enddate,
    wo.duedate,
    CASE WHEN wo.enddate > wo.duedate THEN 'LATE' ELSE 'ON TIME' END AS wo_sla,
    sr.name                                     AS scrap_reason
FROM production.workorder wo
JOIN production.product p     ON p.productid        = wo.productid
LEFT JOIN production.scrapreason sr ON sr.scrapreasonid = wo.scrapreasonid
WHERE wo.productid = %s
ORDER BY wo.startdate DESC
LIMIT 5
```

Cross-domain event count for this product:

```sql
SELECT
    transactiontype,
    CASE transactiontype WHEN 'S' THEN 'Sale' WHEN 'W' THEN 'Work Order' WHEN 'P' THEN 'Purchase' END AS domain,
    COUNT(*)    AS events,
    MIN(transactiondate) AS first,
    MAX(transactiondate) AS last
FROM production.transactionhistory
WHERE productid = %s
GROUP BY transactiontype
ORDER BY transactiontype
```

---

## Step 3 — Purchasing Domain View

For each `productid` from Step 1:

```sql
SELECT
    poh.purchaseorderid,
    CASE poh.status WHEN 1 THEN 'Pending' WHEN 2 THEN 'Approved'
                    WHEN 3 THEN 'Rejected' WHEN 4 THEN 'Complete' END AS po_status,
    v.name                                      AS vendor,
    v.creditrating,
    pod.duedate,
    pod.orderqty,
    pod.receivedqty,
    pod.rejectedqty,
    ROUND(pod.rejectedqty::numeric / NULLIF(pod.receivedqty, 0) * 100, 1) AS rejection_pct,
    CASE WHEN poh.status IN (1,2) AND pod.duedate < NOW()
         THEN 'SUPPLY RISK' ELSE 'OK' END       AS supply_status,
    poh.subtotal + poh.taxamt + poh.freight     AS totaldue
FROM purchasing.purchaseorderheader poh
JOIN purchasing.purchaseorderdetail pod ON pod.purchaseorderid = poh.purchaseorderid
JOIN purchasing.vendor v                ON v.businessentityid  = poh.vendorid
WHERE pod.productid = %s
ORDER BY poh.orderdate DESC
LIMIT 5
```

---

## Step 4 — Synthesis

After running all three domain views, reason across them:

**Coherence checks to apply:**

1. **SLA chain integrity**: if the sales order shipped on time (Step 1) but work orders
   were late (Step 2), the SLA was met despite production delays — flag this.
2. **Scrap impact**: if `scrap_pct > 5%` in Step 2, check if this product also has
   supply risk in Step 3 (double-exposure).
3. **Supply gap**: if Step 3 shows a Pending PO past due for a product that Step 2 shows
   in-progress work orders — active supply risk feeding an open production run.
4. **Event trace coherence**: if Step 2 shows no W events in transactionhistory for a
   product that Step 1 confirms was sold — fulfillment gap (sold but never produced).
5. **Vendor concentration**: if all POs for a product come from one vendor and that
   vendor has a rejection rate > 5% — single-source risk.

---

## Output Format

```
═══════════════════════════════════════════════════════
OPERATIONAL BRIEF  —  Order #<id>  |  <date>
═══════════════════════════════════════════════════════

SALES  [<status>]  SLA: <ON TIME / LATE>
  Channel:    <Online / B2B>
  Territory:  <name>  (<region>)
  Dates:      <orderdate> → due <duedate> → shipped <shipdate>  (<N> days)
  Value:      $<totaldue>

PRODUCTION  (<N> products)
  Product <id>  "<name>"  [<class>]
    Work orders: <n>  |  Scrap: <pct>%  <[reason]>
    Last WO:     #<id>  <status>  <startdate> → <enddate>
  Event trace:  S=<n>  W=<n>  P=<n>

PURCHASING  (<N> vendors)
  Product <id>  via <vendor>  [creditrating: <n>]
    Latest PO:   #<id>  [<status>]  due <date>  recv=<n>/<n>  rej=<n> (<pct>%)
    Supply:      <OK / SUPPLY RISK>

─────────────────────────────────────────────────────
CROSS-DOMAIN FLAGS:
  ⚠ <flag description>
  ⚠ <flag description>

RECOMMENDED ACTION:
  <action — escalate / monitor / no action needed>
═══════════════════════════════════════════════════════
```

---

## Multiple Orders

If asked to brief multiple orders (e.g., "top 5 at-risk"), repeat the full
brief structure for each order, then add a **Summary Table** at the end:

```
SUMMARY TABLE
  #     orderid    value        sla      scrap    supply
  1     <id>       $<n>         LATE     5.2%     RISK
  2     <id>       $<n>         ON TIME  0%       OK
  ...
```

---

## Constraints

- Read-only — never INSERT, UPDATE, or DELETE.
- Always run all three domain steps — never produce a brief from only one domain.
- Do not skip the coherence checks in Step 4 — they are the value of this skill.
- If `anomaly-scanner` produced the input, include the anomaly type and severity
  in the brief header.
- Limit to 5 orders per invocation to keep output readable. If more are needed,
  ask the user to confirm before proceeding.
