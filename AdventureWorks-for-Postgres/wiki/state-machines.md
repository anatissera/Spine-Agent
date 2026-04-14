# State Machines — Status and Lifecycle Columns

Columns whose names contain `status`, `type`, `flag`, `state`, `reason`, `level`, or `class`.
These represent the lifecycle states, classifications, and discrete categories in the database.

---

## Primary lifecycle state machines

### `purchasing.purchaseorderheader.status` — ACTIVE (live state machine)

| Value | Label | Count |
|:---:|---|---:|
| 1 | Pending | 225 |
| 2 | Approved | 12 |
| 3 | Rejected | 86 |
| 4 | Complete | 3,689 |

This is the **only active state machine** in the database with in-flight records. Use for real-time monitoring.

### `sales.salesorderheader.status` — TERMINAL SNAPSHOT

| Value | Label | Count |
|:---:|---|---:|
| 1 | In Process | 0 |
| 2 | Approved | 0 |
| 3 | Backordered | 0 |
| 4 | Rejected | 0 |
| 5 | Shipped | 31,465 |

All records are in terminal state. This is a historical snapshot — no open orders visible.

### `production.transactionhistory.transactiontype` — Cross-domain event type

| Value | Domain | Live count | Archive count |
|:---:|---|---:|---:|
| S | Sale | 74,575 | 46,742 |
| W | Work Order | 31,002 | 41,589 |
| P | Purchase | 7,866 | 922 |

This column is the structural core of the cross-domain event log. S/W/P map to the three operational domains.
Same distribution in `production.transactionhistoryarchive` (archive period: 2022-04-15 → 2024-07-29).

---

## Production states and classifications

### `production.workorder.scrapreasonid` — Scrap classification

| Value | Count | Value | Count |
|:---:|---:|:---:|---:|
| NULL (no scrap) | 71,862 | 13 | 63 |
| 3 | 54 | 11 | 52 |
| 14 | 52 | 16 | 51 |
| 15 | 48 | 9 | 47 |
| 4 | 45 | 6 | 44 |
| 1 | 44 | 2 | 44 |
| 5 | 42 | 12 | 37 |
| 10 | 37 | 8 | 37 |
| 7 | 32 | | |

99% of work orders have no scrap. Scrap reasons are distributed across 16 causes (scrapreasonid 1–16). No single cause dominates.

### `production.product.class`

| Value | Label | Count |
|:---:|---|---:|
| NULL | No class (internal components) | 257 |
| L | Low-end | 97 |
| H | High-end | 82 |
| M | Mid-range | 68 |

### `production.billofmaterials.bomlevel`

| Value | Count |
|:---:|---:|
| 1 | 1,548 |
| 2 | 993 |
| 0 | 103 |
| 3 | 31 |
| 4 | 4 |

Levels 0–4. Level 0 = top-level assembly, higher levels = deeper sub-assemblies.

---

## Sales states and types

### `sales.specialoffer.type`

| Value | Count |
|---|---:|
| Volume Discount | 5 |
| Excess Inventory | 3 |
| Seasonal Discount | 3 |
| Discontinued Product | 2 |
| New Product | 2 |
| No Discount | 1 |

### `sales.salesreason.reasontype`

| Value | Count |
|---|---:|
| Other | 5 |
| Marketing | 4 |
| Promotion | 1 |

### `sales.salesorderheadersalesreason.salesreasonid` — Usage frequency

| Reason ID | Uses |
|:---:|---:|
| 1 | 17,473 |
| 2 | 3,515 |
| 5 | 1,746 |
| 9 | 1,551 |
| 10 | 1,395 |
| 6 | 1,245 |
| 4 | 722 |

7 of 10 reasons are used across 27,647 tagged orders.

### `sales.salestaxrate.taxtype`

| Value | Count |
|:---:|---:|
| 1 | 13 |
| 2 | 3 |
| 3 | 13 |

### `sales.creditcard.cardtype`

| Value | Count |
|---|---:|
| SuperiorCard | 4,839 |
| Distinguish | 4,832 |
| ColonialVoice | 4,782 |
| Vista | 4,665 |

Evenly distributed across 4 card networks (~25% each).

---

## HR and person states

### `humanresources.employee.maritalstatus`

| Value | Count |
|:---:|---:|
| M (Married) | 146 |
| S (Single) | 144 |

### `person.stateprovince.stateprovinceid` — Address concentration

Top state provinces by address count (from `person.address`):

| stateprovinceid | Count |
|:---:|---:|
| 9 | 4,564 |
| 79 | 2,636 |
| 14 | 1,954 |
| 50 | 1,588 |
| 7 | 1,579 |
| 58 | 1,105 |
| 77 | 901 |
| 64 | 795 |

Top 8 state provinces account for 79% of all addresses.

---

## Reference tables (all values count = 1)

These tables define the lookup values for categorical columns. Each row is a distinct valid value.

| Table | Rows | Used by |
|---|---:|---|
| `production.scrapreason` | 16 | workorder.scrapreasonid |
| `person.addresstype` | 6 | businessentityaddress.addresstypeid |
| `person.contacttype` | 20 | businessentitycontact.contacttypeid |
| `sales.salesreason` | 10 | salesorderheadersalesreason.salesreasonid |
| `production.productcategory` | 4 | productsubcategory.productcategoryid |
| `production.productsubcategory` | 37 | product.productsubcategoryid |
| `sales.salesterritory` | 10 | customer.territoryid, salesorderheader.territoryid |
| `purchasing.shipmethod` | 5 | purchaseorderheader.shipmethodid |
