# Purchasing Schema — Database Reference

**Purpose:** Vendor management, purchase order lifecycle, component sourcing, supplier performance.

---

## Tables

### `purchasing.purchaseorderheader` — 4,012 rows — Active state machine

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `purchaseorderid` | integer | NOT NULL | PK. Range 1–4,012 |
| `revisionnumber` | smallint | NOT NULL | Range: 5–21. Avg: 5.08 |
| `status` | smallint | NOT NULL | 1=Pending (225), 2=Approved (12), 3=Rejected (86), 4=Complete (3,689) |
| `employeeid` | integer | NOT NULL | 12 distinct employees placing POs. Range 250–261 |
| `vendorid` | integer | NOT NULL | FK → vendor. 86 distinct vendors |
| `shipmethodid` | integer | NOT NULL | FK → shipmethod. 5 distinct |
| `orderdate` | timestamp | NOT NULL | Range: 2022-04-15 → 2025-09-21 |
| `shipdate` | timestamp | NOT NULL | Range: 2022-04-24 → 2025-10-16 |
| `subtotal` | numeric | NOT NULL | Range: $37 – $997,680. Avg: $15,900 |
| `taxamt` | numeric | NOT NULL | Range: $2.97 – $79,814. Avg: $1,272 |
| `freight` | numeric | NOT NULL | Range: $0.93 – $19,954. Avg: $395 |
| `modifieddate` | timestamp | NOT NULL | Range: 2022-04-24 → 2026-08-11 |

**This is the only domain with a live state machine (statuses 1–4 active).** Use for real-time operational monitoring.

Status distribution:
- 4 (Complete): 3,689 — 91.9%
- 1 (Pending): 225 — 5.6%
- 3 (Rejected): 86 — 2.1%
- 2 (Approved): 12 — 0.3%

---

### `purchasing.purchaseorderdetail` — 8,845 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `purchaseorderid` | integer | NOT NULL | FK → purchaseorderheader. 4,012 distinct |
| `purchaseorderdetailid` | integer | NOT NULL | PK. Range 1–8,845 |
| `duedate` | timestamp | NOT NULL | Range: 2022-04-29 → 2025-10-21 |
| `orderqty` | smallint | NOT NULL | Range: 3–8,000. Avg: 265.5 |
| `productid` | integer | NOT NULL | 265 distinct products (range 1–952). **Cross-domain key** |
| `unitprice` | numeric | NOT NULL | Range: $0.21 – $82.83. Avg: $34.74 |
| `receivedqty` | numeric | NOT NULL | Range: 2–8,000. Avg: 263.1 |
| `rejectedqty` | numeric | NOT NULL | Range: 0–1,250. Avg: 8.2 (3.0% rejection rate) |
| `stockedqty` | numeric | computed | — |
| `modifieddate` | timestamp | NOT NULL | Range: 2022-04-22 → 2026-08-11 |

---

### `purchasing.vendor` — 104 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `businessentityid` | integer | NOT NULL | PK. Range 1,492–1,698. **Links to person schema via businessentityid** |
| `accountnumber` | character varying | NOT NULL | 104 distinct |
| `name` | character varying | NOT NULL | 104 distinct vendor names |
| `creditrating` | smallint | NOT NULL | Range: 1–5. Avg: 1.36 (mostly excellent = 1) |
| `preferredvendorstatus` | boolean | NOT NULL | — |
| `activeflag` | boolean | NOT NULL | — |
| `purchasingwebserviceurl` | character varying | nullable | 94.2% null. Only 6 vendors have a web service URL |
| `modifieddate` | timestamp | NOT NULL | Range: 2022-04-24 → 2023-02-17 |

---

### `purchasing.productvendor` — 460 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `productid` | integer | NOT NULL | 265 distinct products (range 1–952). **Cross-domain key** |
| `businessentityid` | integer | NOT NULL | FK → vendor. 86 distinct vendors |
| `averageleadtime` | integer | NOT NULL | Range: 10–120 days. Avg: 19.45 |
| `standardprice` | numeric | NOT NULL | Range: $0.20 – $78.89. Avg: $34.68 |
| `lastreceiptcost` | numeric | nullable | Range: $0.21 – $82.83. Avg: $36.28 |
| `lastreceiptdate` | timestamp | nullable | Range: 2022-07-21 → 2025-10-21 |
| `minorderqty` | integer | NOT NULL | Range: 1–5,000. Avg: 145.9 |
| `maxorderqty` | integer | NOT NULL | Range: 5–15,000. Avg: 776.5 |
| `onorderqty` | integer | nullable | 66.3% null. Range: 3–8,000 (for non-null) |
| `unitmeasurecode` | character | NOT NULL | FK → production.unitmeasure (by convention) |
| `modifieddate` | timestamp | NOT NULL | Range: 2022-07-21 → 2026-08-11 |

---

### `purchasing.shipmethod` — 5 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `shipmethodid` | integer | NOT NULL | PK. Range 1–5 |
| `name` | character varying | NOT NULL | 5 distinct methods |
| `shipbase` | numeric | NOT NULL | Range: $3.95 – $29.95. Avg: $14.96 |
| `shiprate` | numeric | NOT NULL | Range: $0.99 – $2.99. Avg: $1.75 |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

---

## Foreign keys (intra-schema only)

```
productvendor.businessentityid → vendor.businessentityid
purchaseorderdetail.purchaseorderid → purchaseorderheader.purchaseorderid
purchaseorderheader.shipmethodid → shipmethod.shipmethodid
purchaseorderheader.vendorid → vendor.businessentityid
```

No cross-schema FKs declared.

**Cross-domain joins (by convention):**
- `purchaseorderdetail.productid = production.product.productid` — links PO lines to product catalog
- `purchaseorderdetail.productid = production.transactionhistory.productid WHERE transactiontype='P'` — links to event log
- `vendor.businessentityid = humanresources.employee.businessentityid` — resolves vendor as a business entity (person schema is empty so name resolution fails)

---

## Key operational queries

**Active purchase orders (pending approval):**
```sql
SELECT * FROM purchasing.purchaseorderheader WHERE status IN (1, 2);
```

**Vendor lead times for a specific product:**
```sql
SELECT v.name, pv.averageleadtime, pv.standardprice
FROM purchasing.productvendor pv
JOIN purchasing.vendor v ON v.businessentityid = pv.businessentityid
WHERE pv.productid = <productid>
ORDER BY pv.averageleadtime;
```

**Inbound rejection rate by vendor:**
```sql
SELECT poh.vendorid, v.name,
  SUM(pod.rejectedqty) / NULLIF(SUM(pod.receivedqty + pod.rejectedqty), 0) AS rejection_rate
FROM purchasing.purchaseorderdetail pod
JOIN purchasing.purchaseorderheader poh ON poh.purchaseorderid = pod.purchaseorderid
JOIN purchasing.vendor v ON v.businessentityid = poh.vendorid
GROUP BY poh.vendorid, v.name
ORDER BY rejection_rate DESC;
```
