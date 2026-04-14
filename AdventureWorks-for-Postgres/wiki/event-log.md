# Event Log — Cross-Domain Transaction History

`production.transactionhistory` and `production.transactionhistoryarchive` form the unified operational event log. This is the only table that records activity from three separate domains (Sales, Production, Purchasing) on the same `productid`.

---

## Structure

Both tables share the same schema:

| Column | Type | Notes |
|---|---|---|
| `transactionid` | integer | PK |
| `productid` | integer | FK → production.product. The cross-domain linking key |
| `referenceorderid` | integer | The order that triggered this event (salesorderid, workorderid, or purchaseorderid depending on type) |
| `referenceorderlineid` | integer | The line item within that order |
| `transactiondate` | timestamp | When the event occurred |
| `transactiontype` | character | **S** = Sale, **W** = Work Order, **P** = Purchase |
| `quantity` | integer | Units transacted |
| `actualcost` | numeric | Cost per unit at transaction time |
| `modifieddate` | timestamp | — |

---

## Volume and date ranges

| Table | Rows | Date range | S events | W events | P events |
|---|---:|---|---:|---:|---:|
| `transactionhistory` (live) | 113,443 | 2024-07-30 → 2025-08-02 | 74,575 | 31,002 | 7,866 |
| `transactionhistoryarchive` | 89,253 | 2022-04-15 → 2024-07-29 | 46,742 | 41,589 | 922 |
| **Total** | **202,696** | **2022-04-15 → 2025-08-02** | **121,317** | **72,591** | **8,788** |

The totals confirm the row counts in other tables: 121,317 S-events = 121,317 salesorderdetail rows; 72,591 W-events = 72,591 workorder rows.

---

## How to use for cross-domain queries

**Trace all events for a specific product:**
```sql
SELECT transactiontype, transactiondate, quantity, actualcost, referenceorderid
FROM production.transactionhistory
WHERE productid = <productid>
ORDER BY transactiondate;
```

**Find products with both sales and production activity in the same period:**
```sql
SELECT productid,
  COUNT(*) FILTER (WHERE transactiontype = 'S') AS sale_events,
  COUNT(*) FILTER (WHERE transactiontype = 'W') AS workorder_events,
  COUNT(*) FILTER (WHERE transactiontype = 'P') AS purchase_events
FROM production.transactionhistory
GROUP BY productid
HAVING COUNT(*) FILTER (WHERE transactiontype = 'S') > 0
   AND COUNT(*) FILTER (WHERE transactiontype = 'W') > 0
ORDER BY sale_events DESC;
```

**Monitor for purchase events on high-demand products:**
```sql
SELECT th.productid, p.name, COUNT(*) AS purchase_events,
  MAX(th.transactiondate) AS last_purchase
FROM production.transactionhistory th
JOIN production.product p ON p.productid = th.productid
WHERE th.transactiontype = 'P'
GROUP BY th.productid, p.name
ORDER BY purchase_events DESC;
```

---

## Lifecycle trace — Sample order #51131

This is the highest-value order in the dataset ($187,488). It illustrates the full Sales → Production → Purchasing chain.

### Sales Order (sales domain)

| Field | Value |
|---|---|
| salesorderid | 51131 |
| orderdate | 2024-05-29 |
| duedate | 2024-06-10 |
| shipdate | 2024-06-05 |
| status | 5 (Shipped) |
| totaldue | $187,487.83 |
| territory | Southwest |
| customer | not resolvable (person.person is empty) |

### Work Orders triggered (production domain)

Products: HL and LL Touring Frames in multiple colors and sizes.

| workorderid | Product | Qty | Start | End |
|---:|---|---:|---|---|
| 36568 | HL Touring Frame - Yellow, 60 | 29 | 2024-06-01 | 2024-06-11 |
| 36569 | LL Touring Frame - Yellow, 62 | 38 | 2024-06-01 | 2024-06-11 |
| 36570 | HL Touring Frame - Yellow, 46 | 14 | 2024-06-01 | 2024-06-11 |
| 36571 | HL Touring Frame - Yellow, 50 | 16 | 2024-06-01 | 2024-06-11 |
| 36572 | HL Touring Frame - Yellow, 54 | 24 | 2024-06-01 | 2024-06-11 |
| 36573 | HL Touring Frame - Blue, 46 | 12 | 2024-06-01 | 2024-06-11 |
| 36574 | HL Touring Frame - Blue, 50 | 18 | 2024-06-01 | 2024-06-11 |
| 36575 | HL Touring Frame - Blue, 54 | 57 | 2024-06-01 | 2024-06-11 |
| 36576 | HL Touring Frame - Blue, 60 | 43 | 2024-06-01 | 2024-06-11 (1 unit scrapped — "Thermoform temp too low") |
| 36578 | LL Touring Frame - Blue, 50 | 24 | 2024-06-01 | 2024-06-11 |

Work orders started 3 days after order date (2024-06-01 vs 2024-05-29) and completed 10 days later.
The sale shipped 2024-06-05 — 4 days before work orders ended — suggesting finished inventory was drawn.

### Purchase orders for same product family (purchasing domain)

| PO# | Vendor | Product | Ordered | Received | Rejected |
|---:|---|---|---:|---:|---:|
| 12 | Bicycle Specialists | Touring Pedal | 550 | 550 | 82 |
| 91 | Bicycle Specialists | Touring Pedal | 550 | 550 | 0 |
| 98 | Chicago City Saddles | LL Touring Seat/Saddle | 550 | 550 | 0 |
| 98 | Chicago City Saddles | ML Touring Seat/Saddle | 550 | 550 | 0 |
| 98 | Chicago City Saddles | HL Touring Seat/Saddle | 550 | 550 | 0 |
| 170 | Bicycle Specialists | Touring Pedal | 550 | 550 | 0 |
| 191 | Expert Bike Co | LL Touring Seat/Saddle | 550 | 550 | 27 |
| 191 | Expert Bike Co | ML Touring Seat/Saddle | 550 | 550 | 0 |
| 249 | Bicycle Specialists | Touring Pedal | 550 | 550 | 0 |
| 256 | Chicago City Saddles | LL Touring Seat/Saddle | 550 | 468 | 0 |

Components sourced: Touring Pedals (from Bicycle Specialists), Saddles/Seats (from Chicago City Saddles and Expert Bike Co). PO #12 shows a notable 82-unit rejection from Bicycle Specialists on Touring Pedals.

---

## Trend signals from event log

Comparing live (2024-07-30 → 2025-08-02, 13 months) vs archive (2022-04-15 → 2024-07-29, 27 months):

- **Sales events** grew from 46,742 in 27 months to 74,575 in 13 months → **accelerating sales velocity**
- **Work order events** dropped from 41,589 to 31,002 despite higher sales → fewer WO events per sale (more buy vs make)
- **Purchase events** surged from 922 to 7,866 → **major shift toward purchasing-driven supply** in recent period

These trends suggest the business is scaling sales faster than production capacity, increasingly relying on vendor-sourced components rather than internal manufacturing.
