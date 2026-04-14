---
name: sql-writer
description: >
  Use this skill when asked to write a SQL query for the Adventure Works
  database — "write a query to show sales by territory", "how do I join orders
  to products?", "give me the SQL for top customers", "query the work orders for
  a given product", "show monthly revenue trends", or any request for a
  PostgreSQL SELECT statement against the AdventureWorks schema.
metadata:
  tools:
    - read_file
    - write_file
---

# Skill: SQL Writer

## What This Skill Does

Writes correct PostgreSQL SELECT statements against the Adventure Works Cycles
database. Uses the wiki schema files to verify column names, data types, and
join keys before writing any query.

---

## Step 1 — Look Up the Schema First

Before writing a query, always verify columns and join keys by reading the
relevant wiki file:

| Domain needed | File |
|---|---|
| Sales orders, customers, territories, promotions | `wiki/db-sales.md` |
| Products, work orders, inventory, BOM | `wiki/db-production.md` |
| Purchase orders, vendors | `wiki/db-purchasing.md` |
| Employees, departments, pay | `wiki/db-humanresources.md` |
| Cross-domain joins, FK graph | `wiki/db-fk-graph.md` |
| Row counts (to choose the right table) | `wiki/db-row-counts.md` |

---

## Step 2 — Apply Schema Rules

**Database name:** `Adventureworks` (capital A, no spaces)
**Schemas:** `sales`, `production`, `purchasing`, `humanresources`, `person`
**Always double-quote schema and table names** to preserve case:
```sql
SELECT * FROM "sales"."salesorderheader"
```

**Cross-domain join keys (no FK enforced — join explicitly):**
- `productid` — links `production.product`, `sales.salesorderdetail`,
  `purchasing.purchaseorderdetail`, `production.workorder`
- `businessentityid` — links `humanresources.employee`, `sales.salesperson`,
  `purchasing.vendor` to `person.person`

**No cross-schema FKs exist.** Do not assume the database enforces these — the
application does.

---

## Step 3 — Write the Query

### Common Patterns

**Sales revenue by territory (monthly):**
```sql
SELECT
    t.name                              AS territory,
    date_trunc('month', o.orderdate)   AS month,
    COUNT(*)                            AS orders,
    SUM(o.subtotal)                     AS revenue
FROM "sales"."salesorderheader"  o
JOIN "sales"."salesterritory"    t ON t.territoryid = o.territoryid
GROUP BY t.name, date_trunc('month', o.orderdate)
ORDER BY territory, month;
```

**Top products by units sold:**
```sql
SELECT
    p.name                                                          AS product,
    SUM(d.orderqty)                                                 AS units_sold,
    ROUND(SUM(d.orderqty * d.unitprice * (1.0 - d.unitpricediscount))::numeric, 2) AS revenue
FROM "sales"."salesorderdetail"  d
JOIN "production"."product"      p ON p.productid = d.productid
GROUP BY p.name
ORDER BY units_sold DESC
LIMIT 20;
```

**Online vs B2B channel split:**
```sql
SELECT
    CASE WHEN onlineorderflag THEN 'Online' ELSE 'B2B' END AS channel,
    COUNT(*)                          AS orders,
    SUM(subtotal + taxamt + freight)  AS total_due,
    AVG(subtotal + taxamt + freight)  AS avg_order_value
FROM "sales"."salesorderheader"
GROUP BY onlineorderflag
ORDER BY orders DESC;
```

**Work orders per product (production volume):**
```sql
SELECT
    p.name              AS product,
    COUNT(w.workorderid) AS work_orders,
    SUM(w.orderqty)      AS total_qty
FROM "production"."workorder"  w
JOIN "production"."product"    p ON p.productid = w.productid
GROUP BY p.name
ORDER BY work_orders DESC
LIMIT 20;
```

**Purchase spend by vendor:**
```sql
SELECT
    v.name          AS vendor,
    COUNT(h.purchaseorderid)   AS purchase_orders,
    SUM(h.subtotal)            AS total_spend
FROM "purchasing"."purchaseorderheader" h
JOIN "purchasing"."vendor"              v ON v.businessentityid = h.vendorid
GROUP BY v.name
ORDER BY total_spend DESC;
```

**Sales-to-production trace via transaction history:**
```sql
SELECT
    transactiontype,
    COUNT(*)            AS events,
    MIN(transactiondate) AS first_event,
    MAX(transactiondate) AS last_event
FROM "production"."transactionhistory"
GROUP BY transactiontype
ORDER BY transactiontype;
-- S = Sales, W = Work Order, P = Purchase
```

---

## Step 4 — Format the Output

- Add a `-- Purpose:` comment at the top of every query.
- Align column aliases for readability.
- Use `LIMIT` when the result set could be large and the user hasn't specified.
- Wrap in a fenced SQL code block when writing to chat.
- If saving to a file, use `write_file` to save to a `.sql` file and confirm the path.

---

## Computed Columns — Never Reference Directly

Two columns in AdventureWorks do **not physically exist** in the PostgreSQL port.
Referencing them causes `column does not exist` errors. Always expand inline:

| Virtual column | Table | Use this instead |
|---|---|---|
| `linetotal` | `sales.salesorderdetail` | `orderqty * unitprice * (1.0 - unitpricediscount)` |
| `totaldue` | `sales.salesorderheader` | `subtotal + taxamt + freight` |

Example — correct revenue calculation:
```sql
SUM(d.orderqty * d.unitprice * (1.0 - d.unitpricediscount))  AS revenue
```

---

## Constraints

- Write SELECT only — never INSERT, UPDATE, DELETE, or DDL.
- Always verify column names in the wiki before using them.
- Do not invent column names — the schema is documented; use it.
- Flag any join that crosses schema boundaries as "no FK enforced — verify manually".
- Never use `linetotal` or `totaldue` as column references — expand using the formulas above.
