# Operational Spine — Adventure Works Cycles

The operational spine is the central object that moves through the organization, generating work in each functional domain. Identifying it is the prerequisite for building an AI agent that acts as a system of coherence across the org.

---

## Spine definition

```yaml
spine:
  name: Sales Order
  carrier_table: sales.salesorderheader
  identity_anchor: salesorderid          # links header to detail within Sales
  cross_domain_anchor: productid         # links spine across production, purchasing, and sales
  secondary_anchor: businessentityid     # universal person/entity identity (4 schemas)

  state_machine:
    table: sales.salesorderheader
    column: status
    states:
      - value: 1
        label: "In Process"
      - value: 2
        label: "Approved"
      - value: 3
        label: "Backordered"
      - value: 4
        label: "Rejected"
      - value: 5
        label: "Shipped"
    terminal_state: 5
    note: >
      Active dataset is all terminal-state (status=5 snapshot). Live state tracking
      is present in purchasing.purchaseorderheader (statuses 1–4 active).

  temporal_chain:
    carrier: sales.salesorderheader
    initiated: orderdate
    deadline:  duedate
    completed: shipdate
    avg_cycle_days: 7
    avg_committed_days: 12
    sla_buffer_days: 5
    data_range: "2022-05-30 → 2025-06-29"
    total_orders: 31465

  event_log:
    table: production.transactionhistory
    archive_table: production.transactionhistoryarchive
    linking_column: productid
    event_types:
      - value: S
        label: Sale
        live_count: 74575
      - value: W
        label: Work Order
        live_count: 31002
      - value: P
        label: Purchase
        live_count: 7866
    total_all_events: 202696

  domain_footprint:
    - schema: sales
      role: origin — order is created here; customer, territory, and payment resolved
      key_tables: [salesorderheader, salesorderdetail, customer, salesperson, salesterritory]

    - schema: production
      role: execution — work orders and routing created to fulfill the order
      key_tables: [workorder, workorderrouting, transactionhistory, transactionhistoryarchive, product, productinventory]

    - schema: purchasing
      role: supply — purchase orders created for required components
      key_tables: [purchaseorderheader, purchaseorderdetail, productvendor, vendor]

    - schema: humanresources
      role: capacity — employees execute production; salespeople are resolved here
      key_tables: [employee, employeedepartmenthistory, employeepayhistory]

    - schema: person
      role: identity — customers, employees, and vendors are resolved here via businessentityid
      key_tables: [person, businessentity, address]

  skill_boundaries:
    - skill: SalesSkill
      domain: sales
      operations:
        - query order status and lifecycle dates
        - retrieve customer and territory info
        - check sales rep quota vs actuals
        - detect orders approaching or past due date

    - skill: ProductionSkill
      domain: production
      operations:
        - check work order progress and routing actuals vs schedule
        - query inventory levels by product and location
        - detect scrap events and reasons
        - trace product transactions across S/W/P event types

    - skill: PurchasingSkill
      domain: purchasing
      operations:
        - query vendor lead times and last receipt dates
        - check purchase order status (pending/approved/rejected/complete)
        - flag supply risk for in-demand products

    - skill: HRSkill
      domain: humanresources
      operations:
        - resolve employee by businessentityid
        - check department assignments and history
        - query org hierarchy

    - skill: IdentitySkill
      domain: person
      operations:
        - resolve person, address, and contact info by businessentityid
        - link customers, employees, and vendors to person records
```

---

## Signal scoring

| Signal | Evidence | Score |
|---|---|:---:|
| 1 — Multi-domain identity anchor | `productid` in 3 schemas (production, purchasing, sales). Zero cross-schema FKs — pure convention. | ✓ |
| 2 — State machine | `salesorderheader.status` (all terminal, snapshot). `purchaseorderheader.status` (active, 4 states). `transactionhistory.transactiontype` (S/W/P cross-domain log). | ✓ |
| 3 — Temporal chain | `salesorderheader`: orderdate → duedate → shipdate. Avg 7-day execution, 12-day committed window. | ✓ |
| 4 — Volume hub | `salesorderheader` + `salesorderdetail` at ranks 6 and 1. 3.86 detail rows per header. Downstream: 72K work orders, 202K event entries. | ✓ |
| 5 — Cross-domain causality | `productid` traces sales → production → purchasing. `transactionhistory` records all three domain event types on the same products. | ✓ |

**Score: 5/5 — Confirmed spine.**

---

## Cross-domain causality chain

```
Sales Order placed (sales domain)
  salesorderdetail.productid = X
        ↓ same productid (by convention, no FK)
  Work Order created (production domain)
  workorder.productid = X
        ↓
  Components sourced (purchasing domain)
  purchaseorderdetail.productid = X
        ↓
  All events recorded in unified log:
  transactionhistory.transactiontype = S (sale event)
  transactionhistory.transactiontype = W (work order event)
  transactionhistory.transactiontype = P (purchase event)
```

The key insight: `production.transactionhistory` is the only table that records events from all three operational domains on the same `productid`. It is the structural proof of causality and the best anchor for a Monitor skill.

---

## Integration notes

- All 65 FK constraints are intra-schema — zero cross-schema enforcement.
- The spine exists and generates real cross-domain causality.
- No existing system currently makes it explicit — this is the primary opportunity for an AI operational layer.
- The sales state machine is frozen at terminal state (all shipped). Live monitoring must use `purchaseorderheader` (status 1–4) and `workorderrouting` (schedule vs. actuals).
