# Operational Spine Detection — Methodology

## What this document is

A step-by-step methodology for inferring the **operational spine** of an organization from a relational database dump.
It is designed to be used as context by an AI agent: feed it this document plus the output of the analysis script, and the agent can reason toward a structured spine definition without human guidance.

---

## What is the operational spine?

Every organization operates around one central object — a **deal**, an **order**, a **patient**, a **policy**, a **project** — that moves through multiple functional departments.
Each department works on a different representation of the same root object:

- Sales sees it as a **quote** → **order**
- Production sees it as a **work order**
- Purchasing sees it as a **purchase order**
- Finance sees it as an **invoice**
- Logistics sees it as a **shipment**

This root object, plus the states it moves through and the handoffs it generates across departments, is the **operational spine**.

Identifying it is the prerequisite for building an AI agent that acts as a system of coherence across the organization — because every skill the agent needs to develop is a domain-specific operation on this same object.

---

## The five signals

A spine candidate produces five detectable signals in relational data.
The more signals a table (or column) scores, the stronger the evidence.

### Signal 1 — Multi-domain identity anchor

**What it is:** A column name that appears in tables belonging to 3 or more functionally distinct schemas.

**Why it matters:** When different departments all reference the same ID, that ID is the thread connecting the spine object across the org. It is the structural footprint of the object — the evidence that one thing generates work in multiple places.

**How to detect it:**
For each column name, count how many distinct schemas contain at least one table with that column.
Rank column names by this count descending.

```
column_name          schemas_count   schemas
businessentityid     5               person, hr, production, purchasing, sales
productid            3               production, purchasing, sales
territoryid          2               person, sales
```

**Threshold:** A column appearing in 3+ schemas is a strong identity anchor.
A column appearing in all schemas is the universal identity anchor.

**Note:** This analysis must be done on column names directly, not only on declared FK constraints.
Real enterprise systems frequently enforce cross-domain relationships by convention rather than FK constraints.

---

### Signal 2 — State machine

**What it is:** A table that contains a `status`, `state`, `type`, or similar column with discrete values that represent a lifecycle progression.

**Why it matters:** The spine object is the thing that *moves* through the organization.
Movement means state change. A table with an ordered status progression is likely the spine object or its primary carrier.

**How to detect it:**
1. Find all columns whose names contain: `status`, `state`, `flag`, `type`, `reason`, `level`, `class`
2. For each such column, retrieve distinct values and their row counts
3. Identify columns where values suggest a natural order (numeric codes 1→2→3→4→5, or named stages)

**Interpreting the distribution:**
- All rows in a single state → snapshot dataset (e.g. all completed orders). The state machine exists but the data is end-state only.
- Spread across multiple states → live operational dataset. The state machine is active.
- Single state with a high row count → this is the dominant terminal state. Check whether earlier states exist in an archive table.

**Example:**
```
table                               column    values
sales.salesorderheader              status    5(31465)                   ← all shipped (end-state snapshot)
purchasing.purchaseorderheader      status    4(3689) 1(225) 3(86) 2(12) ← active state machine
production.transactionhistory       type      S(74575) W(31002) P(7866)  ← cross-domain event log
```

The `transactionhistory.type` column is especially significant: values `S` (sale), `W` (work order), `P` (purchase) indicate this table records events from three separate domains on the same product movement — it is a unified event log of the spine.

---

### Signal 3 — Temporal chain

**What it is:** A table that contains multiple date columns representing sequential stages of a process: creation → due → completion.

**Why it matters:** The spine object has a lifecycle in time.
A table with an ordered date chain is modeling that lifecycle — it is tracking when work was initiated, when it was due, and when it was resolved.

**How to detect it:**
Find tables with 2+ date/timestamp columns.
Group the columns by semantic role:

| Role | Common column names |
|------|-------------------|
| Initiated | `orderdate`, `createdate`, `startdate`, `submitteddate` |
| Deadline | `duedate`, `promiseddate`, `expecteddate` |
| Completed | `shipdate`, `closedate`, `enddate`, `completeddate` |

A table that has all three roles populated is modeling a complete lifecycle.

**Example:**
```
sales.salesorderheader:
  orderdate  → duedate  → shipdate
  2022-05-30   2022-06-11  2022-06-06

  avg(shipdate - orderdate) = 7 days
  avg(duedate  - orderdate) = 12 days
```

This tells you: the spine object (sales order) has a 7-day execution window and a 12-day committed window.
Those numbers characterize the operational tempo of the organization.

---

### Signal 4 — Volume hub

**What it is:** A cluster of tables — typically a Header + Detail pair — that together hold the most rows in the database, anchored by the spine object's ID.

**Why it matters:** Data volume follows work.
The tables that accumulate the most rows are the ones the organization writes to most frequently — those are the operational tables, not the reference tables.
The spine object is at the center of the highest-volume table cluster.

**How to detect it:**
1. Rank all tables by row count descending
2. Look for a Header + Detail pattern at the top of the ranking (e.g. `salesorderheader` + `salesorderdetail`)
3. Check whether the Header's primary key appears as a foreign key in other high-volume tables

**Example:**
```
sales.salesorderdetail            121,317   ← detail rows
production.transactionhistory     113,443   ← event log entries
production.workorder               72,591   ← downstream work
sales.salesorderheader             31,465   ← header rows (spine object)
purchasing.purchaseorderdetail      8,845   ← upstream supply work
```

The ratio `detail_rows / header_rows = 121317 / 31465 ≈ 3.9` means each order generates ~4 line items on average.
The existence of downstream work orders (72K rows) and upstream purchase orders triggered by the same products confirms the spine.

---

### Signal 5 — Cross-domain causality

**What it is:** Evidence that a state change in one domain creates records in a different domain.

**Why it matters:** The spine object is the thing that *pulls work* across the organization.
If inserting a sales order causes production work orders to be created, and those work orders cause purchase orders to be created, then the sales order is the root cause object — the spine.

**How to detect it:**
Trace the shared key (from Signal 1) across high-volume tables in different schemas:

```
sales order #51131 (Sales domain)
  ↓ productid shared
  WorkOrder #36569, #36570, #36571... (Production domain)  ← created for same products
  ↓ productid shared
  PurchaseOrder #12, #91, #98... (Purchasing domain)       ← created for same products
```

If the same product IDs that appear in `salesorderdetail` also appear in `workorder` rows with dates that follow the order date, this is temporal evidence of causality — the sale triggered the production, which triggered the purchasing.

---

## Scoring rubric

| Signals matched | Interpretation |
|:-:|---|
| 1 | Possible candidate. Investigate further. |
| 2 | Likely candidate. Check for the missing signals. |
| 3 | Strong candidate. Treat as spine unless a competing object scores higher. |
| 4–5 | Confirmed spine object. |

Apply the rubric to every table in the top 10 by row count plus every table that has a status column.

---

## The inference process

Given the analysis output, follow this sequence:

**Step 1 — Map domains**
List each schema and write one sentence describing what business function it owns.
If schemas are absent, infer domains from table name prefixes or naming clusters.

**Step 2 — Find the identity anchor**
Run the cross-domain column co-occurrence analysis.
The highest-scoring column name is the identity anchor of the spine.

**Step 3 — Find the state machine**
Look for tables that contain the identity anchor column AND have a status/state column.
The table that combines both — an ID that spans domains plus a lifecycle — is the spine carrier.

**Step 4 — Confirm with volume**
Check whether the spine carrier table is in the top 5 by row count (or its detail table is).
If yes, volume confirms it. If no, the spine may be in a lower-volume but higher-criticality position (e.g. a policy object that generates many downstream transactions).

**Step 5 — Confirm with temporal chain**
Check whether the spine carrier has 3 or more date columns in the initiated → due → completed pattern.
If yes, the organization is tracking the lifecycle in time, which confirms the object is being managed as a workflow.

**Step 6 — Confirm with causality**
Trace the identity anchor column across schemas for a sample ID.
Count how many distinct schemas contain a row referencing that ID.
The more schemas touched by a single spine object instance, the stronger the confirmation.

---

## Output format

After completing the inference, produce a structured spine definition:

```yaml
spine:
  name: <human name for the object, e.g. "Sales Order">
  carrier_table: <schema.table that owns the lifecycle, e.g. "sales.salesorderheader">
  identity_anchor: <column name that links it across domains, e.g. "salesorderid">
  secondary_anchor: <universal identity column if present, e.g. "businessentityid">
  
  state_machine:
    column: <status column name>
    states:
      - value: 1
        label: "In Process"
      - value: 5
        label: "Shipped"
    terminal_state: 5
  
  temporal_chain:
    initiated: orderdate
    deadline:  duedate
    completed: shipdate
    avg_cycle_days: 7
  
  domain_footprint:
    - schema: sales
      role: origin — order is created here
      tables: [salesorderheader, salesorderdetail, customer]
    - schema: production
      role: execution — work orders are created to fulfill the order
      tables: [workorder, workorderrouting, transactionhistory]
    - schema: purchasing
      role: supply — purchase orders are created for required components
      tables: [purchaseorderheader, purchaseorderdetail, productvendor]
    - schema: humanresources
      role: capacity — employees execute the work
      tables: [employee, employeedepartmenthistory]
    - schema: person
      role: identity — customers, reps, vendors are resolved here
      tables: [person, businessentity, address]
  
  skill_boundaries:
    - skill: SalesSkill
      domain: sales
      operations: [query order status, retrieve customer info, check territory quota]
    - skill: ProductionSkill
      domain: production
      operations: [check work order progress, query inventory levels, detect scrap]
    - skill: PurchasingSkill
      domain: purchasing
      operations: [query vendor lead times, check PO status, flag supply risk]
    - skill: HRSkill
      domain: humanresources
      operations: [resolve employee by order, check capacity, query org hierarchy]
```

This definition is the input to the agent architecture.
Each `skill_boundary` block becomes a skill module.
The `domain_footprint` defines which tables each skill has read access to.
The `state_machine` defines the events the Monitor mode watches for.
The `temporal_chain` defines the SLA windows the Monitor mode alerts on.

---

## When FK constraints are absent

Many real systems — including this one — do not declare FK constraints across schema boundaries.
Cross-domain relationships are enforced by application code or by convention.

In this case, supplement FK graph analysis with:

1. **Column name matching** — find column names shared across schemas (primary method)
2. **Value overlap sampling** — for candidate ID columns, check whether the set of values in schema A overlaps with the set in schema B (confirming a real join relationship even without a declared FK)
3. **Domain knowledge** — use table and column names to infer relationships (a column called `customerid` in a production table almost certainly references the sales or person domain)

The absence of cross-schema FK constraints is not a failure of the database — it is information about how the organization manages integration. It often means the spine is implicit, held together by shared IDs and application logic rather than database enforcement.
This is the most common case in enterprise systems and the scenario where an AI-native operational layer adds the most value: the spine exists but no system currently makes it explicit.

---

## Limitations and edge cases

| Situation | How to handle |
|---|---|
| All rows in terminal state | The state machine is real but the data is a snapshot. Look for an archive table (e.g. `transactionhistoryarchive`) to reconstruct earlier states. |
| No status column | The lifecycle may be encoded in date columns only (null `enddate` = in progress). Or the state machine lives in a related log table. |
| Multiple spine candidates | Score all candidates. If two objects both score 4+, the organization may have two independent spines (e.g. a product company with both a sales spine and a services spine). Model them separately. |
| No cross-schema column overlap | The database may be a single-schema monolith. Apply the same signals within sub-namespaces inferred from table name prefixes. |
| Very low row counts | The database may be a configuration/reference system, not an operational one. The spine lives upstream; this is a supporting system. |
