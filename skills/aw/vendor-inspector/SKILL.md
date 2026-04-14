---
name: vendor-inspector
description: >
  Use this skill when asked about vendors, purchase orders, or supply status:
  "what is the status of PO #1234?", "which vendors have high rejection rates?",
  "is there supply risk for product X?", "show me pending purchase orders",
  "which POs are overdue?", "how reliable is vendor Y?", "show purchasing spend
  by vendor", or any question about the purchasing domain. This is the only
  skill that operates on a live state machine (purchaseorderheader.status has
  active Pending and Approved records). This is the Purchasing domain view of
  the operational spine.
metadata:
  tools:
    - run_sql
---

# Skill: Vendor Inspector

## What This Skill Does

Queries the purchasing domain of AdventureWorks — the only domain with a live,
active state machine. Produces a **vendor/supply state card** for a vendor,
product, or purchase order.

This is the supply side of the spine:
`salesorderdetail.productid` → `workorder.productid` → `purchaseorderdetail.productid`

---

## Critical Context: The Live State Machine

`purchasing.purchaseorderheader.status` is the **only active state machine** in
the entire database. All sales orders are terminal (status=5 Shipped). This is
where live monitoring happens.

| Status | Label | Count |
|:---:|---|---:|
| 1 | Pending | 225 |
| 2 | Approved | 12 |
| 3 | Rejected | 86 |
| 4 | Complete | 3,689 |

**Monitoring priority:** Status=1 (Pending) records past their `duedate` = supply risk.

---

## Authorized Tables

| Table | Schema | Purpose |
|---|---|---|
| `purchaseorderheader` | `purchasing` | PO root — status, dates, totals, vendor |
| `purchaseorderdetail` | `purchasing` | PO line items — product, qty, received, rejected |
| `vendor` | `purchasing` | Vendor profile — credit rating, active flag |
| `productvendor` | `purchasing` | Product-vendor relationship — lead times, standard price |
| `shipmethod` | `purchasing` | Shipping method lookup |

---

## Step 1 — Resolve the Input

| Input type | Strategy |
|---|---|
| Single `purchaseorderid` | Query header + detail directly |
| `vendorid` or vendor name | Filter `purchaseorderheader` by vendorid |
| `productid` | Join `purchaseorderdetail` on productid |
| "Pending / at risk" | `WHERE status IN (1, 2) AND duedate < NOW()` |
| "Vendor performance" | Aggregate rejectedqty/receivedqty across all POs |
| No input | Run the supply risk scan (Step 4) |

---

## Step 2 — Query the PO Header

```sql
-- Purpose: purchase order header state card
SELECT
    poh.purchaseorderid,
    poh.revisionnumber,
    poh.status,
    CASE poh.status
        WHEN 1 THEN 'Pending'
        WHEN 2 THEN 'Approved'
        WHEN 3 THEN 'Rejected'
        WHEN 4 THEN 'Complete'
    END                                         AS status_label,
    poh.orderdate,
    poh.shipdate,
    poh.subtotal,
    poh.taxamt,
    poh.freight,
    poh.subtotal + poh.taxamt + poh.freight     AS totaldue,
    poh.vendorid,
    v.name                                      AS vendor_name,
    v.creditrating,
    v.preferredvendorstatus,
    v.activeflag,
    sm.name                                     AS ship_method
FROM purchasing.purchaseorderheader poh
JOIN purchasing.vendor    v  ON v.businessentityid  = poh.vendorid
JOIN purchasing.shipmethod sm ON sm.shipmethodid    = poh.shipmethodid
WHERE poh.purchaseorderid = %s  -- or adjust filter
```

---

## Step 3 — Query the PO Line Items

```sql
-- Purpose: PO line items with reception quality
SELECT
    pod.purchaseorderdetailid,
    pod.productid,
    pod.duedate,
    pod.orderqty,
    pod.unitprice,
    pod.receivedqty,
    pod.rejectedqty,
    pod.stockedqty,
    ROUND(
        CASE WHEN pod.receivedqty > 0
             THEN pod.rejectedqty::numeric / pod.receivedqty * 100
             ELSE 0
        END, 1
    )                                           AS rejection_pct,
    CASE WHEN pod.duedate < NOW() AND pod.receivedqty < pod.orderqty
         THEN 'OVERDUE'
         ELSE 'OK'
    END                                         AS receipt_status
FROM purchasing.purchaseorderdetail pod
WHERE pod.purchaseorderid = %s
ORDER BY pod.duedate ASC
```

---

## Step 4 — Vendor Performance Profile

When asked about a vendor's reliability or overall performance:

```sql
-- Purpose: vendor reliability summary
SELECT
    v.name                                      AS vendor,
    v.creditrating,
    COUNT(DISTINCT poh.purchaseorderid)         AS total_pos,
    SUM(pod.orderqty)                           AS total_ordered,
    SUM(pod.receivedqty)                        AS total_received,
    SUM(pod.rejectedqty)                        AS total_rejected,
    ROUND(
        SUM(pod.rejectedqty)::numeric /
        NULLIF(SUM(pod.receivedqty), 0) * 100, 2
    )                                           AS overall_rejection_pct,
    AVG(pv.averageleadtime)                     AS avg_lead_time_days,
    MAX(pv.lastreceiptdate)                     AS last_receipt_date,
    SUM(poh.subtotal + poh.taxamt + poh.freight) AS total_spend
FROM purchasing.vendor v
JOIN purchasing.purchaseorderheader poh  ON poh.vendorid        = v.businessentityid
JOIN purchasing.purchaseorderdetail pod  ON pod.purchaseorderid = poh.purchaseorderid
LEFT JOIN purchasing.productvendor pv    ON pv.businessentityid = v.businessentityid
WHERE v.businessentityid = %s  -- or remove for all vendors
GROUP BY v.businessentityid, v.name, v.creditrating
```

---

## Step 5 — Supply Risk Scan (no input required)

When no specific PO or vendor is given, scan for supply risk:

```sql
-- Purpose: identify pending POs past their due date (supply risk)
SELECT
    poh.purchaseorderid,
    poh.status,
    CASE poh.status WHEN 1 THEN 'Pending' WHEN 2 THEN 'Approved' END AS status_label,
    poh.orderdate,
    poh.shipdate,
    v.name                                      AS vendor,
    pod.productid,
    pod.duedate,
    pod.orderqty,
    pod.receivedqty,
    pod.orderqty - pod.receivedqty              AS outstanding_qty,
    EXTRACT(DAY FROM (NOW() - pod.duedate))     AS days_overdue
FROM purchasing.purchaseorderheader poh
JOIN purchasing.purchaseorderdetail pod ON pod.purchaseorderid  = poh.purchaseorderid
JOIN purchasing.vendor v                ON v.businessentityid   = poh.vendorid
WHERE poh.status IN (1, 2)
  AND pod.duedate < NOW()
  AND pod.receivedqty < pod.orderqty
ORDER BY days_overdue DESC
LIMIT 20
```

---

## Step 6 — Apply Reasoning

- **Credit rating** 1–5: lower = better. Flag vendors with creditrating >= 4.
- **Rejection rate > 5%**: escalation threshold — flag for vendor review.
- **Lead time adherence**: compare `lastreceiptdate - orderdate` to `averageleadtime`.
- **Supply concentration**: if one vendor supplies > 60% of a product's volume, flag single-source risk.
- **Pending past due**: these are the highest-priority alerts — product is ordered but not received.

---

## Format the Vendor/Supply State Card

```
VENDOR: <name>  (creditrating: <n>/5)  [Active / Inactive]
  Total POs:      <n>  |  Total spend: $<amount>
  Rejection rate: <pct>%  |  Avg lead time: <n> days
  Last receipt:   <date>

OPEN PURCHASE ORDERS:
  PO #<id>  [<status>]  ordered=<n>  received=<n>  due=<date>  [OVERDUE <n> days]
  ...

SUPPLY RISK ITEMS:
  productid <id>  outstanding=<n> units  <n> days overdue  via <vendor>
```

---

## Constraints

- Read-only — never INSERT, UPDATE, or DELETE.
- This is the only skill authorized to query `purchasing.*` tables.
- Do not compute lead times from `salesorderheader` — use `productvendor.averageleadtime`.
- Always flag `status IN (1,2)` records past their `duedate` — these are active supply risks.
