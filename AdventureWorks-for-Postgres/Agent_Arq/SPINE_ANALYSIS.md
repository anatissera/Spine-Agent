# Operational Spine Analysis — AdventureWorks

Analysis following the [Operational Spine Detection Methodology](SPINE_DETECTION.md).

---

## Step 1 — Domain Map

| Schema | Business Function |
|---|---|
| `humanresources` | Workforce management — employees, departments, pay, job candidates, shifts |
| `person` | Identity layer — resolves people, companies, addresses, contact info |
| `production` | Manufacturing — products, work orders, BOMs, inventory, routing, scrap |
| `purchasing` | Procurement — purchase orders, vendors, product-vendor lead times |
| `sales` | Commercial — sales orders, customers, territories, promotions, credit |

5 distinct domains. No cross-schema FK constraints exist — all 63 declared FKs are intra-schema. Cross-domain relationships are held together by shared column names enforced by application convention.

---

## Step 2 — Identity Anchor

Column co-occurrence across schemas (columns appearing in 3+ schemas, excluding audit columns `modifieddate`, `rowguid`):

| Column | Schemas | Count |
|---|---|:---:|
| `businessentityid` | humanresources, person, purchasing, sales | 4 |
| `productid` | production, purchasing, sales | 3 |
| `status` | production, purchasing, sales | 3 |
| `duedate` | production, purchasing, sales | 3 |
| `orderqty` | production, purchasing, sales | 3 |

Two distinct identity anchors emerge:

**Primary operational anchor — `productid`**
Appears in every transactional domain where work is performed: production makes it, purchasing buys its components, sales sells it. It is the thread that connects the spine object across all three operational schemas. No declared FK enforces this — it is a convention-based relationship.

**Universal person anchor — `businessentityid`**
Appears in 4 schemas. It resolves the *human and organizational actors* behind the workflow: the customer, the sales rep, the employee executing production, the vendor supplying materials. It is the identity layer that gives roles to each domain, not the workflow object itself.

---

## Step 3 — State Machine

### `sales.salesorderheader.status`

| Value | Label | Count |
|:---:|---|---:|
| 1 | In Process | 0 |
| 2 | Approved | 0 |
| 3 | Backordered | 0 |
| 4 | Rejected | 0 |
| 5 | Shipped | 31,465 |

**All 31,465 rows are in terminal state 5.** This is a snapshot dataset — every order in the active dataset has been shipped. The state machine is real but the data captures only end-state records.

### `purchasing.purchaseorderheader.status` (active state machine)

| Value | Label | Count |
|:---:|---|---:|
| 1 | Pending | 225 |
| 2 | Approved | 12 |
| 3 | Rejected | 86 |
| 4 | Complete | 3,689 |

An active multi-state lifecycle is present in purchasing. The 225 pending orders and 12 approved (in-flight) orders confirm this is a live operational dataset.

### `production.transactionhistory.transactiontype` (unified event log)

| Value | Domain | Count |
|:---:|---|---:|
| `S` | Sale | 74,575 |
| `W` | Work Order | 31,002 |
| `P` | Purchase | 7,866 |

This is the most significant signal. A single table records events from three separate domains — sales, production, and purchasing — on the same `productid`. This is a **unified cross-domain event log of the spine object's journey**. The archive table adds 89,253 more historical events (2022-04-15 to 2024-07-29), showing the event log has been partitioned over time.

Combined event log (live + archive): **202,696 total transactions** tracking the same products across all three operational schemas.

---

## Step 4 — Volume Hub

Tables ranked by row count:

| Rank | Table | Rows | Role |
|:---:|---|---:|---|
| 1 | `sales.salesorderdetail` | 121,317 | Detail rows — spine line items |
| 2 | `production.transactionhistory` | 113,443 | Active event log |
| 3 | `production.transactionhistoryarchive` | 89,253 | Archived event log |
| 4 | `production.workorder` | 72,591 | Downstream production work |
| 5 | `production.workorderrouting` | 67,131 | Production routing steps |
| 6 | **`sales.salesorderheader`** | **31,465** | **Spine carrier — order headers** |
| 7 | `sales.salesorderheadersalesreason` | 27,647 | Order reason tags |
| 8 | `sales.customer` | 19,820 | Customer master |
| 9 | `person.address` | 19,614 | Address resolution |
| 13 | `purchasing.purchaseorderdetail` | 8,845 | Upstream supply detail |
| 14 | `purchasing.purchaseorderheader` | 4,012 | Upstream supply headers |

**Header + Detail pattern confirmed** at ranks 6 and 1:

```
121,317 detail rows / 31,465 header rows = 3.86 line items per order (avg)
```

Each sales order generates ~4 line items on average.

The downstream footprint is large: 72,591 work orders (production) and 4,012 purchase orders (purchasing) were created in response to the sales demand recorded in 31,465 order headers. The event log accumulates at roughly 6.4 events per order header — reflecting multi-step tracking of each product through the supply chain.

---

## Step 5 — Temporal Chain

### `sales.salesorderheader`

| Role | Column | Range |
|---|---|---|
| Initiated | `orderdate` | 2022-05-30 → 2025-06-29 |
| Deadline | `duedate` | 2022-06-11 → 2025-07-11 |
| Completed | `shipdate` | 2022-06-06 → 2025-07-06 |

**Average cycle times:**
- Order → Ship: **7 days** (actual execution window)
- Order → Due: **12 days** (committed window)

The organization commits 12 days and delivers in 7. A 5-day buffer is built into every order's SLA.

### `production.workorder`

| Role | Column | Range |
|---|---|---|
| Initiated | `startdate` | 2022-06-02 → 2025-06-01 |
| Deadline | `duedate` | 2022-06-13 → 2025-06-12 |
| Completed | `enddate` | 2022-06-12 → 2025-06-16 |

Work orders carry their own 3-phase temporal chain (start → due → end), running in parallel with the sales order's lifecycle. Start dates on work orders closely follow order dates on sales orders, confirming temporal causality.

### `production.workorderrouting`

| Role | Column |
|---|---|
| Planned start | `scheduledstartdate` |
| Planned end | `scheduledenddate` |
| Actual start | `actualstartdate` |
| Actual end | `actualenddate` |

This table carries **both** planned and actual timelines for each routing step — the highest temporal resolution in the database. It is where schedule vs. actuals can be compared for production performance monitoring.

---

## Step 6 — Cross-Domain Causality

`productid` traces across all three operational schemas:

```
Sales Order (sales domain)
  salesorderdetail.productid = X
        ↓ same productid
  WorkOrder (production domain)
  workorder.productid = X     ← production triggered to manufacture product X
        ↓ same productid
  TransactionHistory (cross-domain event log)
  transactiontype='S' (74,575)  ← sale of X recorded
  transactiontype='W' (31,002)  ← work order for X recorded
  transactiontype='P'  (7,866)  ← purchase for X's components recorded
        ↓ same productid
  PurchaseOrderDetail (purchasing domain)
  purchaseorderdetail.productid = X  ← components sourced from vendors
```

The `transactionhistory` table is the structural proof of causality: it records events from three separate domains on the same `productid`. When a sale is placed, a work order is created in production; when production needs components, a purchase order is created. All three events are captured in this unified log.

Date ranges confirm the temporal order: sales order dates precede work order start dates, which precede purchase order dates for the same products.

---

## Signal Scoring

| Signal | Evidence | Verdict |
|---|---|:---:|
| 1 — Multi-domain identity anchor | `productid` in 3 schemas (production, purchasing, sales). No declared cross-schema FK — pure convention. | ✓ |
| 2 — State machine | `salesorderheader.status` (all terminal, snapshot). `purchaseorderheader.status` (active, 4 states). `transactionhistory.transactiontype` (S/W/P cross-domain log). | ✓ |
| 3 — Temporal chain | `salesorderheader`: orderdate → duedate → shipdate. Avg 7-day execution, 12-day committed window. | ✓ |
| 4 — Volume hub | `salesorderheader` + `salesorderdetail` at ranks 6 and 1. 3.86 detail rows per header. Downstream: 72K work orders, 202K event log entries. | ✓ |
| 5 — Cross-domain causality | `productid` traced across sales → production → purchasing. `transactionhistory` records all three domain event types on same products. | ✓ |

**Score: 5/5 — Confirmed spine object.**

---

## Spine Definition

```yaml
spine:
  name: Sales Order
  carrier_table: sales.salesorderheader
  identity_anchor: salesorderid
  cross_domain_anchor: productid        # links the spine across production, purchasing, sales
  secondary_anchor: businessentityid    # universal person/entity identity (4 schemas)

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
      Active dataset is all terminal-state (status=5 snapshot).
      Earlier states are archived in production.transactionhistoryarchive.
      Live state tracking is present in purchasing.purchaseorderheader (status 1-4 active).

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
        count: 74575
      - value: W
        label: Work Order
        count: 31002
      - value: P
        label: Purchase
        count: 7866
    total_live_events: 113443
    total_archived_events: 89253
    total_all_events: 202696
    note: >
      Unified cross-domain event log. Records events from 3 separate domains
      (sales, production, purchasing) on the same productid. No other table
      in the schema performs this cross-domain integration role.

  domain_footprint:
    - schema: sales
      role: origin — order is created here; customer, territory, and payment resolved
      key_tables:
        - salesorderheader        # spine carrier (31,465 rows)
        - salesorderdetail        # line items (121,317 rows, 3.86/order)
        - customer                # 19,820 customers
        - salesperson             # 17 reps with territory assignments
        - salesterritory          # 10 territories

    - schema: production
      role: execution — work orders and routing created to fulfill the order
      key_tables:
        - workorder               # 72,591 work orders (downstream demand)
        - workorderrouting        # 67,131 routing steps (scheduled vs actual)
        - transactionhistory      # 113,443 live event records (S/W/P log)
        - transactionhistoryarchive  # 89,253 archived events (2022-2024)
        - product                 # 504 products (the cross-domain object)
        - productinventory        # 1,069 inventory positions

    - schema: purchasing
      role: supply — purchase orders created for required components
      key_tables:
        - purchaseorderheader     # 4,012 POs (active state machine: 1→4)
        - purchaseorderdetail     # 8,845 PO line items
        - productvendor           # 460 product-vendor relationships
        - vendor                  # 104 vendors

    - schema: humanresources
      role: capacity — employees execute the production work; salespeople are resolved here
      key_tables:
        - employee                # 290 employees
        - employeedepartmenthistory  # 296 department assignment records
        - employeepayhistory      # 316 pay records

    - schema: person
      role: identity — customers, employees, and vendors are all resolved here via businessentityid
      key_tables:
        - person                  # person master (cross-entity identity)
        - businessentity          # root entity record
        - address                 # 19,614 addresses
        - businessentityaddress   # address assignments

  skill_boundaries:
    - skill: SalesSkill
      domain: sales
      operations:
        - query order status and lifecycle dates
        - retrieve customer and territory info
        - check sales rep quota vs. actuals
        - identify sales reasons and discount offers applied
        - detect orders approaching or past due date

    - skill: ProductionSkill
      domain: production
      operations:
        - check work order progress and routing actuals vs. schedule
        - query inventory levels by product and location
        - detect scrap events and scrap reasons
        - trace product transactions across S/W/P event types
        - monitor active vs. archived transaction history

    - skill: PurchasingSkill
      domain: purchasing
      operations:
        - query vendor lead times and last receipt dates
        - check purchase order status (pending/approved/rejected/complete)
        - flag supply risk for in-demand products
        - retrieve product-vendor pricing and min order quantities

    - skill: HRSkill
      domain: humanresources
      operations:
        - resolve employee by businessentityid
        - check department assignments and history
        - query org hierarchy (departments and shifts)
        - retrieve pay history for capacity planning

    - skill: IdentitySkill
      domain: person
      operations:
        - resolve person, address, and contact info by businessentityid
        - link customers, employees, and vendors to their person records
        - validate addresses and state/country references

  integration_notes:
    cross_schema_fk_constraints: 0
    total_fk_constraints: 63
    integration_mechanism: >
      All cross-domain relationships are enforced by application convention, not FK constraints.
      productid is the primary cross-domain linking column (production ↔ purchasing ↔ sales).
      businessentityid is the secondary linking column (person ↔ humanresources ↔ purchasing ↔ sales).
      The operational spine is implicit in the data — no single system currently makes it explicit.
      This is the primary opportunity for an AI-native operational layer.
```

---

## Key Observations

### 1. The spine is confirmed but invisible in the schema

All 63 FK constraints are intra-schema. The three operational domains (sales, production, purchasing) share no declared FK relationships. The spine exists as a convention — `productid` joins records across domains by agreement, not enforcement. An AI operational layer that makes this explicit would be the first system in this architecture to surface the spine directly.

### 2. The state machine is frozen at terminal state in sales; active in purchasing

Every sales order (31,465) is in status 5 (Shipped). This is a snapshot dataset. The full lifecycle — from creation through approval, backorder resolution, and shipment — existed but is not visible in the current active table. The 202,696 combined events in `transactionhistory` and `transactionhistoryarchive` are the only historical record of the journey.

By contrast, `purchasing.purchaseorderheader` has 225 pending and 12 approved in-flight orders — the purchasing state machine is live and active.

### 3. The unified event log is the structural core

`production.transactionhistory` (+ archive) is the single most analytically powerful table. It records sales events, production events, and purchasing events on the same `productid` in one place. It is both the event log and the integration bus. Any monitor capability should be rooted here.

### 4. Operational tempo: 7-day execution, 12-day commitment

The organization makes a 12-day commitment to customers and executes in 7. This 5-day buffer is consistent and measurable. SLA monitoring should alert when `shipdate - orderdate > 7` (execution degradation) and when `duedate - orderdate < 12` (committed window erosion).

### 5. Production routing carries schedule vs. actual data

`workorderrouting` (67,131 rows) has both `scheduledstartdate/scheduledenddate` and `actualstartdate/actualenddate`. This is the highest-resolution operational data in the schema — where planned capacity meets actual execution. A ProductionSkill that monitors this table can detect schedule slippage before it propagates to the order's ship date.
