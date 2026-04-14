# Adventure Works Cycles — Agent Wiki Index

This wiki is the knowledge base for an AI agent operating on the Adventure Works Cycles database.
Each file is scoped to one topic so the agent can load exactly what it needs.

---

## Navigation guide

| Question type | File |
|---|---|
| What does the company do? What is its scale and structure? | [company-overview.md](company-overview.md) |
| Revenue, margins, order volume, channel mix, customers, territories, workforce | [business-metrics.md](business-metrics.md) |
| SLA performance, fulfillment rate, scrap, vendor quality, production efficiency | [operational-health.md](operational-health.md) |
| What is the operational spine? How does work flow across domains? | [spine.md](spine.md) |
| Known data gaps, empty tables, quality flags, limitations | [data-quality.md](data-quality.md) |
| **Sales** schema — tables, columns, FKs, key stats | [db-sales.md](db-sales.md) |
| **Production** schema — tables, columns, FKs, key stats | [db-production.md](db-production.md) |
| **Purchasing** schema — tables, columns, FKs, key stats | [db-purchasing.md](db-purchasing.md) |
| **Human Resources** schema — tables, columns, FKs, key stats | [db-humanresources.md](db-humanresources.md) |
| **Person/Identity** schema — tables, columns, FKs, key stats | [db-person.md](db-person.md) |
| Row counts for every table | [db-row-counts.md](db-row-counts.md) |
| All declared foreign key relationships | [db-fk-graph.md](db-fk-graph.md) |
| Status, type, and lifecycle columns with value distributions | [state-machines.md](state-machines.md) |
| Transaction history (event log) — structure, patterns, lifecycle trace | [event-log.md](event-log.md) |

---

## Domain map

| Schema | Business function | Key operational tables |
|---|---|---|
| `sales` | Order management, customer relationships, territory, promotions | `salesorderheader`, `salesorderdetail`, `customer`, `salesperson`, `salesterritory` |
| `production` | Manufacturing, product catalog, inventory, event log | `product`, `workorder`, `workorderrouting`, `transactionhistory`, `productinventory` |
| `purchasing` | Procurement, vendor management, component supply | `purchaseorderheader`, `purchaseorderdetail`, `vendor`, `productvendor` |
| `humanresources` | Employees, departments, pay, shifts | `employee`, `department`, `employeepayhistory` |
| `person` | Universal identity layer — people, addresses, contacts | `person`, `businessentity`, `address` ⚠️ mostly empty |

---

## Cross-domain integration rules

- **Zero cross-schema FK constraints.** All 65 declared FKs are intra-schema.
- **Primary cross-domain key:** `productid` — links `production`, `purchasing`, and `sales`.
- **Secondary cross-domain key:** `businessentityid` — links `humanresources`, `person`, `purchasing`, and `sales`.
- Cross-domain joins must be written explicitly; the database does not enforce them.
- See [spine.md](spine.md) for the full integration map and causality chain.

---

## Quick reference

| Metric | Value |
|---|---|
| Total sales orders (May 2022 – Jun 2025) | 31,465 |
| Annualized revenue | ~$40M/year |
| Gross margin | ~42% |
| Avg order-to-ship | 7 days |
| Total customers | 19,820 |
| Employees | 290 |
| Vendors | 104 |
| Total work orders | 72,591 |
| Cross-domain event log entries | 202,696 |
