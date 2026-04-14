# Production Schema — Database Reference

**Purpose:** Product catalog, manufacturing (work orders, routing), bill of materials, inventory, scrap, and the unified cross-domain event log.

---

## Tables

### `production.product` — 504 rows — Cross-domain anchor

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `productid` | integer | NOT NULL | PK. Range 1–999. **Primary cross-domain key** |
| `name` | character varying | NOT NULL | 504 distinct |
| `productnumber` | character varying | NOT NULL | 504 distinct |
| `makeflag` | boolean | NOT NULL | True = manufactured internally |
| `finishedgoodsflag` | boolean | NOT NULL | True = sellable finished good |
| `color` | character varying | nullable | 49.2% null. 9 distinct colors |
| `safetystocklevel` | smallint | NOT NULL | Range: 4–1,000. Avg: 535 |
| `reorderpoint` | smallint | NOT NULL | Range: 3–750 |
| `standardcost` | numeric | NOT NULL | Range: $0 – $2,171. Avg: $259 |
| `listprice` | numeric | NOT NULL | Range: $0 – $3,578. Avg: $439 |
| `size` | character varying | nullable | 58.1% null. 18 distinct values |
| `sizeunitmeasurecode` | character | nullable | 65.1% null |
| `weightunitmeasurecode` | character | nullable | 59.3% null |
| `weight` | numeric | nullable | 59.3% null. Range: 2.12–1,050 |
| `daystomanufacture` | integer | NOT NULL | Range: 0–4. Avg: 1.1 |
| `productline` | character | nullable | 44.8% null. 4 distinct (R, M, T, S) |
| `class` | character | nullable | 51.0% null. H/M/L + null |
| `style` | character | nullable | 58.1% null. 3 distinct |
| `productsubcategoryid` | integer | nullable | 41.5% null. FK → productsubcategory. 37 distinct |
| `productmodelid` | integer | nullable | 41.5% null. 119 distinct |
| `sellstartdate` | timestamp | NOT NULL | Range: 2019-04-30 → 2024-05-29. 4 distinct dates |
| `sellenddate` | timestamp | nullable | 80.6% null. End dates: 2023-05-29 or 2024-05-28 |
| `discontinueddate` | timestamp | nullable | 100% null — no discontinued products |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

Product classes: H (High) = 82, M (Mid) = 68, L (Low) = 97, null (components) = 257.
Products actually sold: 266 distinct (range 707–999). Products manufactured: 238 distinct.

---

### `production.workorder` — 72,591 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `workorderid` | integer | NOT NULL | PK. Range 1–72,591 |
| `productid` | integer | NOT NULL | FK → product. 238 distinct (range 3–999) |
| `orderqty` | integer | NOT NULL | Range: 1–39,570. Avg: 62.1 |
| `scrappedqty` | smallint | NOT NULL | Range: 0–673. Avg: 0.15 |
| `startdate` | timestamp | NOT NULL | Range: 2022-06-02 → 2025-06-01 |
| `enddate` | timestamp | nullable | Range: 2022-06-12 → 2025-06-16 |
| `duedate` | timestamp | NOT NULL | Range: 2022-06-13 → 2025-06-12 |
| `scrapreasonid` | smallint | nullable | 99.0% null. Only 729 WOs had scrap. FK → scrapreason |
| `modifieddate` | timestamp | NOT NULL | — |

Scrap reason distribution — see [state-machines.md](state-machines.md).

---

### `production.workorderrouting` — 67,131 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `workorderid` | integer | NOT NULL | FK → workorder. 42,625 distinct |
| `productid` | integer | NOT NULL | 149 distinct products (range 514–999) |
| `operationsequence` | smallint | NOT NULL | Range: 1–7. Avg: 5.11 |
| `locationid` | smallint | NOT NULL | FK → location. 7 distinct (range 10–60) |
| `scheduledstartdate` | timestamp | NOT NULL | Range: 2022-06-02 → 2025-06-01 |
| `scheduledenddate` | timestamp | NOT NULL | Range: 2022-06-13 → 2025-06-12 |
| `actualstartdate` | timestamp | nullable | Range: 2022-06-02 → 2025-06-16 |
| `actualenddate` | timestamp | nullable | Range: 2022-06-14 → 2025-06-27 |
| `actualresourcehrs` | numeric | nullable | Range: 1.0–4.1. Avg: 3.41 |
| `plannedcost` | numeric | NOT NULL | Range: $14.50–$92.25. Avg: $51.96 |
| `actualcost` | numeric | nullable | Range: $14.50–$92.25. Avg: $51.96 ⚠️ identical to planned |
| `modifieddate` | timestamp | NOT NULL | — |

Use `scheduledstartdate`/`scheduledenddate` vs `actualstartdate`/`actualenddate` for schedule variance. `actualcost = plannedcost` always — do not use for cost variance analysis.

---

### `production.transactionhistory` — 113,443 rows — Live event log

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `transactionid` | integer | NOT NULL | PK. Range 100,000–213,442 |
| `productid` | integer | NOT NULL | FK → product. 441 distinct |
| `referenceorderid` | integer | NOT NULL | 37,118 distinct. Range 417–75,123 |
| `referenceorderlineid` | integer | NOT NULL | Range 0–71 |
| `transactiondate` | timestamp | NOT NULL | Range: 2024-07-30 → 2025-08-02 |
| `transactiontype` | character | NOT NULL | S=Sale (74,575), W=Work Order (31,002), P=Purchase (7,866) |
| `quantity` | integer | NOT NULL | Range: 1–39,270. Avg: 35 |
| `actualcost` | numeric | NOT NULL | Range: $0–$2,443. Avg: $241 |
| `modifieddate` | timestamp | NOT NULL | — |

This is the **unified cross-domain event log**. A single productid will appear here with type S (when sold), W (when manufactured), and P (when purchased as a component).

---

### `production.transactionhistoryarchive` — 89,253 rows — Archived event log

Same schema as `transactionhistory`. Period: 2022-04-15 → 2024-07-29.
transactionid range: 1–89,253. Distribution: S=46,742, W=41,589, P=922.

---

### `production.productinventory` — 1,069 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `productid` | integer | NOT NULL | FK → product. 432 distinct |
| `locationid` | smallint | NOT NULL | FK → location. 14 distinct |
| `shelf` | character varying | NOT NULL | — |
| `bin` | smallint | NOT NULL | Range: 0–61 |
| `quantity` | smallint | NOT NULL | Range: 0–924. Avg: 314 |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | Range: 2019-03-31 → 2025-08-11 |

---

### `production.billofmaterials` — 2,679 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `billofmaterialsid` | integer | NOT NULL | PK. Range 1–3,482 |
| `productassemblyid` | integer | nullable | 3.8% null. FK → product. 238 distinct assemblies |
| `componentid` | integer | NOT NULL | FK → product. 325 distinct components |
| `startdate` | timestamp | NOT NULL | Range: 2021-03-03 → 2021-12-22 |
| `enddate` | timestamp | nullable | 92.6% null |
| `bomlevel` | smallint | NOT NULL | Range: 0–4 (level 1=1,548, 2=993, 0=103, 3=31, 4=4) |
| `perassemblyqty` | numeric | NOT NULL | Range: 1–41 |
| `unitmeasurecode` | character | NOT NULL | FK → unitmeasure |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `production.productcosthistory` — 395 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `productid` | integer | NOT NULL | FK → product. 293 distinct (range 707–999) |
| `startdate` | timestamp | NOT NULL | 3 dates: 2022-05-30, 2023-05-29, 2024-05-29 (annual) |
| `enddate` | timestamp | nullable | 49.4% null |
| `standardcost` | numeric | NOT NULL | Range: $0.86–$2,171. Avg: $434 |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `production.productlistpricehistory` — 395 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `productid` | integer | NOT NULL | FK → product. 293 distinct (range 707–999) |
| `startdate` | timestamp | NOT NULL | 3 dates: 2022-05-30, 2023-05-29, 2024-05-29 (annual) |
| `enddate` | timestamp | nullable | 49.4% null |
| `listprice` | numeric | NOT NULL | Range: $2.29–$3,578.27. Avg: $748 |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `production.productsubcategory` — 37 rows | `production.productcategory` — 4 rows

Hierarchy: productcategory (4) → productsubcategory (37) → product.
4 categories: Bikes, Components, Clothing, Accessories.

### `production.scrapreason` — 16 rows

16 distinct scrap reasons (IDs 1–16, 1 row each). Used in `workorder.scrapreasonid`.

### `production.location` — 14 rows

14 manufacturing locations (IDs 1–60). costrate: 0–$25. availability: 0–120 hrs.
Only 7 locations are used in `workorderrouting`.

### `production.unitmeasure` — 38 rows

Unit measure codes used for product size, weight, and BOM quantities.

### `production.productreview` — 4 rows

Product reviews for 3 products (IDs 709, 937, and one more). Ratings: 2–5. Dates: Sep–Nov 2013.

---

## Foreign keys (intra-schema only)

```
billofmaterials.componentid → product.productid
billofmaterials.productassemblyid → product.productid
billofmaterials.unitmeasurecode → unitmeasure.unitmeasurecode
product.productsubcategoryid → productsubcategory.productsubcategoryid
product.sizeunitmeasurecode → unitmeasure.unitmeasurecode
product.weightunitmeasurecode → unitmeasure.unitmeasurecode
productcosthistory.productid → product.productid
productdocument.productid → product.productid
productinventory.locationid → location.locationid
productinventory.productid → product.productid
productlistpricehistory.productid → product.productid
productmodelproductdescriptionculture.cultureid → culture.cultureid
productproductphoto.productid → product.productid
productreview.productid → product.productid
productsubcategory.productcategoryid → productcategory.productcategoryid
transactionhistory.productid → product.productid
workorder.productid → product.productid
workorder.scrapreasonid → scrapreason.scrapreasonid
workorderrouting.locationid → location.locationid
workorderrouting.workorderid → workorder.workorderid
```

No cross-schema FKs declared. To join production to sales, join `workorder.productid = salesorderdetail.productid` (by convention). To join to purchasing, join `transactionhistory.productid = purchaseorderdetail.productid`.
