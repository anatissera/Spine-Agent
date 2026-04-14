---
name: order-inspector
description: >
  Use this skill when asked about a specific sales order or a set of orders:
  "what is the status of order #43659?", "show me all orders for territory X",
  "which orders shipped late?", "give me the line items for this order",
  "what did this customer buy?", "show orders placed in Q1 2024", or any question
  that requires retrieving, filtering, or summarizing sales order data from the
  live database. This is the Sales domain view of the operational spine.
metadata:
  tools:
    - run_sql
---

# Skill: Order Inspector

## What This Skill Does

Retrieves and analyzes sales order data from the live AdventureWorks database.
Produces a structured **order state card** for one or more orders.
This is the atom — its output is consumed by `order-briefing` and `anomaly-scanner`.

---

## Authorized Tables

| Table | Schema | Purpose |
|---|---|---|
| `salesorderheader` | `sales` | Root spine object — dates, status, totals, channel |
| `salesorderdetail` | `sales` | Line items — products, quantities, prices |
| `salesterritory` | `sales` | Territory name and region group |
| `salesperson` | `sales` | Sales rep link (via businessentityid) |
| `customer` | `sales` | Customer record (personid may be NULL — known data gap) |
| `specialoffer` | `sales` | Discount type applied to line items |
| `salesorderheadersalesreason` | `sales` | Sale reason codes |

Do not query tables outside this list. For production or purchasing data, defer to
`production-inspector` or `vendor-inspector`.

---

## Step 1 — Resolve the Input

Determine what the user is asking for:

| Input type | Strategy |
|---|---|
| Single `orderid` | Query header + detail directly |
| Filter (territory, date, rep) | Build WHERE clause on `salesorderheader` |
| "Latest / recent" | `ORDER BY orderdate DESC LIMIT N` |
| "At risk / overdue" | `WHERE shipdate > duedate` or `WHERE duedate < NOW()` |
| "High value" | `ORDER BY totaldue DESC LIMIT N` |

---

## Step 2 — Query the Order Header

```sql
-- Purpose: order header state card
SELECT
    soh.salesorderid,
    soh.orderdate,
    soh.duedate,
    soh.shipdate,
    soh.status,
    CASE soh.status
        WHEN 1 THEN 'In Process'
        WHEN 2 THEN 'Approved'
        WHEN 3 THEN 'Backordered'
        WHEN 4 THEN 'Rejected'
        WHEN 5 THEN 'Shipped'
    END                                         AS status_label,
    soh.onlineorderflag,
    CASE WHEN soh.onlineorderflag THEN 'Online' ELSE 'B2B' END AS channel,
    soh.subtotal,
    soh.taxamt,
    soh.freight,
    soh.totaldue,
    soh.customerid,
    soh.salespersonid,
    st.name                                     AS territory,
    st."group"                                  AS territory_region,
    EXTRACT(DAY FROM (soh.shipdate - soh.orderdate)) AS actual_cycle_days,
    EXTRACT(DAY FROM (soh.duedate  - soh.orderdate)) AS committed_days,
    CASE
        WHEN soh.shipdate > soh.duedate THEN 'LATE'
        WHEN soh.shipdate <= soh.duedate THEN 'ON TIME'
        ELSE 'UNKNOWN'
    END                                         AS sla_status
FROM sales.salesorderheader soh
JOIN sales.salesterritory st ON st.territoryid = soh.territoryid
WHERE soh.salesorderid = %s   -- replace with actual id or adjust WHERE clause
```

**SLA reference:** avg cycle = 7 days, committed window = 12 days, buffer = 5 days.

---

## Step 3 — Query the Line Items

```sql
-- Purpose: order line items
SELECT
    sod.salesorderdetailid,
    sod.productid,
    sod.orderqty,
    sod.unitprice,
    sod.unitpricediscount,
    sod.linetotal,
    so.description                              AS offer_description,
    so.discountpct
FROM sales.salesorderdetail sod
LEFT JOIN sales.specialoffer so ON so.specialofferid = sod.specialofferid
WHERE sod.salesorderid = %s
ORDER BY sod.linetotal DESC
```

---

## Step 4 — Apply Reasoning

After retrieving the data, reason about:

- **SLA status**: was `shipdate <= duedate`? If not, flag as LATE.
- **Cycle time**: compare `actual_cycle_days` to the 7-day avg. >14 days is an outlier.
- **Channel**: Online orders tend to have lower AOV; B2B orders are larger and rep-driven.
- **Discount pressure**: `unitpricediscount > 0` on line items — check `offer_description`.
- **Missing salesperson**: `salespersonid IS NULL` on B2B orders is a data quality flag.

---

## Step 5 — Format the Order State Card

Output as a structured card with these sections:

```
ORDER #<id>
  Status:      <label>  |  SLA: <ON TIME / LATE>
  Channel:     <Online / B2B>
  Territory:   <name>  (<region>)
  Dates:       Ordered <date> → Due <date> → Shipped <date>  (<N> days)
  Value:       $<subtotal> subtotal  /  $<totaldue> total due
  Sales rep:   <businessentityid or "unassigned">

LINE ITEMS (<N> products):
  productid <id>  qty=<n>  unit=$<price>  total=$<linetotal>  [<offer>]
  ...
```

---

## Constraints

- Read-only — never INSERT, UPDATE, or DELETE.
- Do not join to `person.person` for customer names — those tables are empty in this dataset.
- Do not fabricate SLA verdicts — compute them from actual date columns.
- If no orders match the filter, say so clearly and suggest a broader query.
