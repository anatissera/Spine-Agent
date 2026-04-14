# Adventure Works Cycles — Business Intelligence Report

**Data period:** May 2022 – June 2025 (37 months)
**Source:** AdventureWorks operational database (PostgreSQL)
**Methodology:** [Operational Spine Detection](SPINE_DETECTION.md) + [Spine Analysis](SPINE_ANALYSIS.md)

---

## Executive Summary

Adventure Works Cycles is a mid-size bicycle manufacturer operating across five functional domains: Sales, Production, Purchasing, Human Resources, and a shared identity layer (Person). Over the 37-month data window the company processed **31,465 sales orders** with a total value of **~$123.2M** (~$40M/year run rate), manufactured **72,591 work orders** across 238 distinct products, and sourced components through **4,012 purchase orders** from 104 vendors.

The business is predominantly a direct-to-consumer online operation (87.9% of orders) with a secondary B2B channel managed by 17 sales reps across 10 territories. The operational model is vertically integrated: most finished goods are manufactured internally from sourced components, with an average production cycle of ~10 days and a customer-facing SLA of 7 days from order to ship.

The core operational spine — the Sales Order — achieves 100% fulfillment in the active dataset (all orders shipped, zero rejections), consistent sub-7-day delivery, and a healthy ~42% gross margin. The main structural risk is the complete absence of cross-schema FK enforcement: the three operational domains (Sales, Production, Purchasing) are integrated by convention on `productid` only, with no system currently providing a coherent cross-domain view.

---

## 1. Company Profile

| Attribute | Value |
|---|---|
| Industry | Bicycle manufacturing |
| Product lines | Bikes, Components, Clothing, Accessories |
| Employees | 290 (across 16 departments, 6 groups) |
| Active customers | 19,820 |
| B2B accounts (stores) | 701 |
| Vendors | 104 (86 active on POs) |
| Sales reps | 17 (across 10 territories) |
| Product catalog | 504 SKUs (4 categories, 37 subcategories) |
| Manufacturing locations | 14 production locations |
| Data span | May 2022 – June 2025 |

The company manufactures premium touring and road bicycle components and assemblies — evident from work order samples (HL Touring Frame, Touring Pedal, HL/LL Touring Saddle) and product naming conventions (HL = High-end, ML = Mid-line, LL = Low-end). The three-tier product class system (H/M/L) spans a wide price range ($2.29 to $3,578.27 list price).

---

## 2. Revenue & Commercial Performance

### Order Volume

| Metric | Value |
|---|---|
| Total orders (37 months) | 31,465 |
| Total order line items | 121,317 |
| Avg line items per order | 3.86 |
| Avg units per line | 2.27 |
| Avg units per order | ~8.8 |
| Distinct products sold | 266 of 504 (52.8%) |

### Revenue

| Metric | Value |
|---|---|
| Total gross revenue (subtotal) | ~$109.8M |
| Total tax collected | ~$10.2M |
| Total freight revenue | ~$3.2M |
| **Total billed (totaldue)** | **~$123.2M** |
| **Annualized revenue** | **~$40M/year** |
| Avg order value (subtotal) | $3,491 |
| Avg order value (totaldue) | $3,916 |
| Min order value | $1.52 |
| Max order value | $187,488 |

### Sales Channel Mix

| Channel | Orders | Share |
|---|---|---|
| Online (direct) | ~27,658 | 87.9% |
| B2B / sales rep | ~3,807 | 12.1% |

The B2B channel is identified by the presence of a `purchaseordernumber` on the order and an assigned `salespersonid`. The online channel dominates by volume; the B2B channel likely carries a higher average order value given enterprise purchasing patterns.

### International Exposure

44.4% of all sales orders reference a currency rate (non-USD transactions). With 2,514 distinct exchange rate records over the period, the company carries meaningful multi-currency exposure across its international customer base.

---

## 3. Product Portfolio

### Catalog Structure

| Level | Count |
|---|---|
| Categories | 4 |
| Subcategories | 37 |
| Total SKUs | 504 |
| SKUs with subcategory (catalog / finished goods) | 296 (58.7%) |
| SKUs without subcategory (raw materials / components) | 208 (41.3%) |
| SKUs actually sold in period | 266 |
| SKUs discontinued | 0 |

### Pricing & Margin

| Metric | All Products | Active Products (w/ price history) |
|---|---|---|
| Avg list price | $438.67 | $747.66 |
| Avg standard cost | $258.60 | $434.27 |
| **Gross margin** | **41.1%** | **41.9%** |
| Min list price | $0.00 | $2.29 |
| Max list price | $3,578.27 | $3,578.27 |

~42% gross margin is consistent across both views of the catalog. The gap between all-product and active-product averages ($439 vs $748) reflects the large pool of raw material and component SKUs priced at or near $0 that are consumed internally, not sold to end customers.

### Product Classes

| Class | Products | Profile |
|---|---|---|
| No class (internal / components) | 257 (51%) | Raw materials, sub-assemblies |
| L — Low-end | 97 (19%) | Entry-level catalog products |
| H — High-end | 82 (16%) | Premium catalog products |
| M — Mid-range | 68 (14%) | Mid-tier catalog products |

### Pricing Cycle

Price and cost changes are tracked for 293 active products (productid 707–999) across 3 revision dates (May 2022, May 2023, May 2024), indicating an annual pricing cycle. No products are discontinued in the current catalog.

### Discount Structure

16 active special offers with discounts from 0% to 50% (avg 22%). However, the average applied discount in order detail is effectively 0.00 — the vast majority of order lines transact at full list price. Discounting is rare and targeted.

| Offer type | Count |
|---|---|
| Volume Discount | 5 |
| Excess Inventory | 3 |
| Seasonal Discount | 3 |
| Discontinued Product | 2 |
| New Product | 2 |
| No Discount | 1 |

---

## 4. Production Operations

### Work Order Volume

| Metric | Value |
|---|---|
| Total work orders (37 months) | 72,591 |
| Distinct products manufactured | 238 |
| Avg order quantity per WO | 62.1 units |
| Work orders per sales order | ~2.3 |
| Production cycle (start → end) | ~10 days |

### Routing Efficiency

| Metric | Value |
|---|---|
| Total routing steps | 67,131 |
| Avg operations per work order | 5.11 |
| Distinct production locations used | 7 (of 14 total) |
| Avg actual resource hours / step | 3.41 hrs |
| Avg planned cost per step | $51.96 |
| Avg actual cost per step | $51.96 |

The actual cost per routing step is **identical to planned cost** across all 67,131 records. This either reflects exceptional production cost control or indicates that actual costs are auto-populated from planned values — a data quality point worth verifying before relying on variance analysis.

### Scrap

| Metric | Value |
|---|---|
| Work orders with scrap | 729 |
| Scrap rate (WO count) | 1.00% |
| Avg scrapped units per WO | 0.15 |
| Estimated total scrapped units | ~10,900 |
| Distinct scrap reasons | 16 |

At 1.0% of work orders, scrap is low. The 16 scrap reason categories are evenly distributed (32–63 WOs per reason), suggesting no single systematic defect dominates — scrap appears random rather than process-driven.

### Event Log — Cross-Domain Transaction History

`production.transactionhistory` records all product movements across Sales (S), Work Orders (W), and Purchases (P) on a single `productid`, functioning as a unified operational event log spanning three domains.

| Period | S events | W events | P events | Total |
|---|---|---|---|---|
| Live (Jul 2024 – Aug 2025) | 74,575 | 31,002 | 7,866 | 113,443 |
| Archive (Apr 2022 – Jul 2024) | 46,742 | 41,589 | 922 | 89,253 |
| **All-time** | **121,317** | **72,591** | **8,788** | **202,696** |

The live period (13 months) contains significantly more Sales events (74,575) than the archive (27 months, 46,742) — a sign of accelerating sales velocity. The near-total absence of Purchase events in the archive (922) vs the live period (7,866) suggests a major shift toward purchasing-driven supply in the most recent period.

---

## 5. Supply Chain & Purchasing

### Purchase Order Volume

| Metric | Value |
|---|---|
| Total POs (37 months) | 4,012 |
| Total PO line items | 8,845 |
| Avg lines per PO | 2.20 |
| Active vendors (placed POs) | 86 of 104 |
| Employees placing POs | 12 |
| PO value range | $37 – $997,680 |
| Avg PO subtotal | $15,900 |
| **Estimated total PO spend** | **~$63.8M** |
| **Annualized PO spend** | **~$20.8M/year** |

PO spend represents approximately **52% of gross revenue**, consistent with a vertically-integrated manufacturer that both makes and sources components.

### Purchase Order Status

| Status | Count | Share |
|---|---|---|
| Complete | 3,689 | 91.9% |
| Pending | 225 | 5.6% |
| Rejected | 86 | 2.1% |
| Approved (in-flight) | 12 | 0.3% |

237 POs are currently active (pending + approved) — the purchasing pipeline is live.

### Vendor Quality

| Metric | Value |
|---|---|
| Total vendors | 104 |
| Avg credit rating | 1.36 / 5 (excellent) |
| Vendors with web service URL | 6 (5.8%) |
| Avg vendor lead time | 19.45 days |
| Lead time range | 10 – 120 days |
| Avg received quantity / PO line | 263 units |
| Avg rejected quantity / PO line | 8.2 units |
| **Vendor rejection rate** | **3.0%** |

At 3.0% average rejection rate, inbound quality is adequate. The max lead time of 120 days (vs average 19 days) indicates at least some long-lead specialty components — a supply risk concentration to investigate.

---

## 6. Workforce

### Headcount

| Metric | Value |
|---|---|
| Total employees | 290 |
| Active employees | 290 (100%) |
| Distinct job titles | 67 |
| Departments | 16 |
| Department groups | 6 |
| Shifts | 3 |
| Open positions / job candidates | 0 |

### Tenure

| Metric | Value |
|---|---|
| Hire date range | Jun 2006 – May 2013 |
| Most recent hire | May 2013 |
| Birth year range | 1951 – 1991 |
| Marital status | 50.3% Married / 49.7% Single |
| Active dept assignments | 98% current (2% have ended) |

The hire date cutoff at May 2013 is notable: **no employee in the dataset was hired after 2013**. Combined with zero job candidates, the workforce appears static for 12+ years.

### Compensation

| Metric | Value |
|---|---|
| Pay rate range | $6.50 – $125.50 / hr |
| Avg pay rate | $17.76 / hr |
| Distinct pay rates | 66 |
| Pay frequency | Majority biweekly |
| Avg pay changes per employee | 1.09 |

The avg rate of $17.76/hr is weighted by the large number of hourly production workers. The top rate ($125.50/hr) represents senior leadership or specialized technical roles. At 1.09 pay change records per employee, compensation has been largely static.

---

## 7. Sales Force & Territories

### Territory Performance

| Metric | Value |
|---|---|
| Territories | 10 |
| Country / region groups | 3 |
| Territory salesYTD total | ~$52.8M |
| Territory saleslastyear total | ~$32.7M |
| Top territory YTD | $10,510,854 |
| Bottom territory YTD | $2,402,177 |
| Revenue share — top territory | 19.9% |

### Sales Rep Performance

| Metric | Value |
|---|---|
| Total reps | 17 |
| Reps with territory assignment | 14 (82.4%) |
| Reps without territory | 3 (17.6%) |
| Quota tiers | $250,000 or $300,000 per period |
| Avg salesYTD | $2,133,976 |
| Top rep YTD | $4,251,369 |
| Bottom rep YTD | $172,524 |
| **Performance spread (top / bottom)** | **24.6×** |
| Avg commission rate | 1% (range: 0–2%) |
| Avg bonus | $2,860 |

The 24.6× spread between top and bottom rep performance is unusually wide. It likely reflects territory size differences, but also points to a potential coaching or quota-assignment problem. Three reps hold no territory — they may be on an overlay, transitional, or house-account model.

### Purchase Reasons (Order Attribution)

27,647 sales reason tags are attached across orders. The dominant reason (ID 1, cited 17,473 times) is likely price-driven. The distribution falls sharply after the top reason, with marketing and promotion reasons trailing. Only 1 of 10 defined reasons is classified as "Promotion"; 4 are "Marketing" and 5 are "Other" — suggesting reason categorization is loose.

---

## 8. Operational Health

### Customer SLA

| Metric | Value |
|---|---|
| Orders shipped | 31,465 / 31,465 (100%) |
| Orders rejected | 0 |
| Orders in process | 0 |
| Avg days order → ship | **7.0 days** |
| Avg days order → due | **12.0 days** |
| Built-in SLA buffer | **+5 days** |

The company commits 12 days and delivers in 7, with 100% fulfillment in the active dataset. The 5-day buffer is consistent and measurable — a concrete SLA baseline for monitoring.

### Production Health

| Metric | Value |
|---|---|
| Avg work order cycle time | ~10 days |
| Avg routing steps | 5.11 |
| Scrap rate | 1.0% |
| Cost variance (planned vs actual) | 0% — data quality flag |

### Purchasing Health

| Metric | Value |
|---|---|
| PO completion rate | 91.9% |
| PO rejection rate | 2.1% |
| Active in-flight POs | 237 |
| Avg vendor lead time | 19.45 days |
| Inbound rejection rate | 3.0% |

---

## 9. Inventory Snapshot

| Metric | Value |
|---|---|
| Products with inventory positions | 432 |
| Inventory locations | 14 |
| Total location-product records | 1,069 |
| Avg quantity per position | 314 units |
| Min quantity | 0 |
| Max quantity | 924 |
| Avg safety stock | 535 units |
| Safety stock range | 4 – 1,000 units |

---

## 10. Customer Base

| Metric | Value |
|---|---|
| Total customers | 19,820 |
| Individual consumers | ~19,119 (96.5%) |
| Store / B2B accounts | 701 (3.5%) |
| Territories represented | 10 |
| Credit cards on file | 19,118 |
| Credit card types | 4 (evenly distributed ~25% each) |

The 701 store accounts are 3.5% of the customer base but likely account for a disproportionate share of revenue given typical B2B order sizes.

---

## 11. Risks & Notable Flags

### Structural Risks

**No cross-domain integration layer.**
All 63 FK constraints are intra-schema. Sales, Production, and Purchasing share zero declared FK relationships. `productid` links them by convention only. No existing system provides a coherent view of a single product's journey from sales order → work order → purchase order. This is the primary architectural gap.

**Single-point supply risk possible.**
86 active vendors supply 265 products. The 120-day max lead time (vs 19-day average) indicates at least one long-lead specialty component. If that component is single-sourced, it represents a supply chain bottleneck that is currently invisible in any cross-domain view.

**Live order monitoring is blind in Sales.**
The sales order state machine is frozen at terminal state (all 31,465 orders are shipped). Real-time alerting on sales orders is not possible against the current active data — the only live state machine is in `purchaseorderheader` (237 active POs). Monitoring must anchor on purchasing and `workorderrouting` (schedule vs. actuals), not on `salesorderheader`.

**Sales rep performance is highly uneven.**
24.6× spread from top to bottom rep with 3 unassigned reps. Without a cross-domain view linking rep → order → product → territory performance, coaching and rebalancing is operating blind.

### Data Quality Flags

**Planned vs. actual production cost are always identical.**
`workorderrouting.actualcost` equals `workorderrouting.plannedcost` exactly across all 67,131 routing records. Production cost variance is effectively invisible — either the system doesn't capture actuals, or actuals auto-populate from planned values.

**Workforce data is frozen at 2013.**
No hires after May 2013, zero job candidates. If revenue has accelerated (suggested by event log trends), the company is growing on static headcount. Either the dataset is historical or the operation is being scaled through automation / outsourcing not visible in this schema.

### Dataset Gaps (sample database limitations)

| Table | Rows | Impact |
|---|---|---|
| `person.person` | 0 | No customer name resolution |
| `person.businessentity` | 0 | No entity identity layer |
| `sales.store` | 0 | No B2B account detail |
| `humanresources.jobcandidate` | 0 | No talent pipeline |
| `sales.shoppingcartitem` | 3 | No e-commerce funnel data |
| Credit card expiry years | 2005–2008 | All cards expired |

---

## 12. Summary Scorecard

| Domain | Rating | Notes |
|---|---|:---|
| Revenue | Strong | ~$40M/year, ~42% gross margin, minimal discounting |
| Fulfillment | Excellent | 100% shipped, 7-day avg, 5-day buffer on every order |
| Production | Good | 1% scrap, 10-day cycle — cost variance data is unreliable |
| Supply chain | Good | 91.9% PO completion, 3% inbound rejection — lead time risk possible |
| Sales force | Mixed | 24.6× top/bottom spread, 3 reps unassigned to territory |
| Workforce | Stable | 290 employees, no observable growth since 2013 |
| Data integration | Weak | Zero cross-schema FKs — spine is implicit, never made explicit |
| Observability | Limited | Terminal-state sales snapshot; live monitoring must anchor on purchasing |

---

*All monetary totals are estimates: per-record averages × row counts. Actual totals may differ by distribution skew. Data period: May 2022 – June 2025.*
