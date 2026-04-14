# Operational Health — Adventure Works Cycles

---

## Customer SLA

| Metric | Value |
|---|---|
| Orders shipped | 31,465 / 31,465 (100%) |
| Orders rejected | 0 |
| Orders in process | 0 |
| **Avg order → ship** | **7.0 days** |
| **Avg order → due (committed)** | **12.0 days** |
| Built-in SLA buffer | +5 days on every order |
| Order date range | 2022-05-30 → 2025-06-29 |

The active `salesorderheader` table is a **terminal-state snapshot** — all 31,465 orders have status = 5 (Shipped). There are no open, in-process, or rejected orders visible in the current data. Real-time SLA monitoring must anchor on `purchasing.purchaseorderheader` and `production.workorderrouting` instead.

Alert thresholds derived from this data:
- Execution degradation: `shipdate - orderdate > 7 days`
- SLA window erosion: `duedate - orderdate < 12 days`

---

## Production efficiency

| Metric | Value |
|---|---|
| Work order cycle time | ~10 days (startdate → enddate) |
| Avg routing operations per WO | 5.11 steps |
| Production locations active | 7 of 14 |
| Avg actual resource hrs per step | 3.41 hrs |
| Work orders with scrap | 729 (1.0%) |
| Avg scrapped units per WO | 0.15 |
| Estimated total scrapped units | ~10,900 |
| Planned vs actual cost variance | 0% ⚠️ data quality flag |

Scrap is distributed evenly across 16 causes (32–63 WOs per reason). No single defect dominates — scrap appears random.

`workorderrouting` holds both **scheduled** and **actual** dates, enabling schedule-vs-actual comparison per routing step:
- `scheduledstartdate` / `scheduledenddate` — planned window
- `actualstartdate` / `actualenddate` — real execution

Actual and planned costs are identical across all 67,131 routing records ($51.96 avg). This is a data quality flag — actual costs may be auto-populated from planned values, making variance analysis unreliable.

---

## Purchasing pipeline

| Metric | Value |
|---|---|
| PO completion rate | 91.9% |
| PO rejection rate | 2.1% |
| Active in-flight POs | 237 (225 pending + 12 approved) |
| Avg vendor lead time | 19.45 days |
| Lead time range | 10 – 120 days |
| Inbound component rejection rate | 3.0% |

Status values for `purchasing.purchaseorderheader.status`:

| Value | Label | Count |
|:---:|---|---:|
| 1 | Pending | 225 |
| 2 | Approved | 12 |
| 3 | Rejected | 86 |
| 4 | Complete | 3,689 |

The purchasing state machine is **live and active** — the only domain with in-flight records.

---

## Cross-domain event log

`production.transactionhistory` records product movements across all three operational domains using `transactiontype`:

| Type | Domain | Live count | Archive count | Total |
|:---:|---|---:|---:|---:|
| S | Sale | 74,575 | 46,742 | 121,317 |
| W | Work Order | 31,002 | 41,589 | 72,591 |
| P | Purchase | 7,866 | 922 | 8,788 |
| **Total** | | **113,443** | **89,253** | **202,696** |

Live period: Jul 2024 – Aug 2025. Archive period: Apr 2022 – Jul 2024.

The live period (13 months) contains more Sales events than the archive (27 months), indicating accelerating sales velocity. The near-total absence of P events in the archive vs the live period suggests a major shift toward purchasing-driven supply recently.

---

## Vendor quality

| Metric | Value |
|---|---|
| Total vendors | 104 |
| Avg credit rating | 1.36 / 5 (excellent end of scale) |
| Avg vendor lead time | 19.45 days |
| Lead time range | 10 – 120 days |
| Inbound rejection rate | 3.0% |
| Vendors with web service URL | 6 (5.8%) |

The 120-day max lead time (vs 19-day avg) indicates at least one long-lead specialty component. If single-sourced, this is a supply risk.
