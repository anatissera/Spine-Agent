# Data Quality — Known Gaps and Flags

This file documents data limitations, empty tables, and quality flags that affect agent reasoning.

---

## Empty tables (0 rows)

These tables exist in the schema but contain no data. Queries against them will return empty results.

| Table | Expected content | Impact |
|---|---|---|
| `person.person` | Person master record (name, type, email promotion) | Cannot resolve customer or employee names |
| `person.businessentity` | Root entity record for all persons and orgs | Identity layer non-functional |
| `person.businessentityaddress` | Links entities to addresses | Cannot join people to addresses |
| `person.businessentitycontact` | Links entities to contact persons | Cannot resolve contact relationships |
| `person.emailaddress` | Email addresses per person | No email data available |
| `person.password` | Login credentials | N/A for operational queries |
| `person.personphone` | Phone numbers per person | No phone data available |
| `person.phonenumbertype` | Phone type lookup | N/A |
| `person.vadditionalcontactinfo` | Additional contact info (view) | Empty |
| `sales.store` | B2B store accounts with demographics | Cannot resolve store names or details |
| `sales.vindividualcustomer` | Individual customer view | Empty (depends on person tables) |
| `sales.vpersondemographics` | Customer demographics view | Empty |
| `sales.vsalesperson` | Sales rep view with full details | Empty |
| `sales.vsalespersonsalesbyfiscalyears` | Fiscal year pivot view | Empty |
| `sales.vstorewithaddresses` | Store + address view | Empty |
| `sales.vstorewithcontacts` | Store + contact view | Empty |
| `sales.vstorewithdemographics` | Store + demographics view | Empty |
| `humanresources.jobcandidate` | Job applicants | No talent pipeline data |
| `humanresources.vemployee` | Employee full details view | Empty (depends on person) |
| `humanresources.vemployeedepartment` | Employee + dept view | Empty |
| `humanresources.vemployeedepartmenthistory` | Employee dept history view | Empty |
| `humanresources.vjobcandidate` | Job candidate view | Empty |
| `humanresources.vjobcandidateeducation` | Candidate education view | Empty |
| `humanresources.vjobcandidateemployment` | Candidate employment view | Empty |
| `production.document` | Product documents | Empty |
| `production.illustration` | Product illustrations | Empty |
| `production.productdescription` | Product descriptions | Empty |
| `production.productmodel` | Product model definitions | Empty |
| `production.productphoto` | Product photos | Empty |
| `production.vproductmodelcatalogdescription` | Product catalog view | Empty |
| `production.vproductmodelinstructions` | Manufacturing instructions view | Empty |
| `purchasing.vvendorwithaddresses` | Vendor + address view | Empty |
| `purchasing.vvendorwithcontacts` | Vendor + contact view | Empty |

---

## Critical functional gaps

**Customer name resolution is impossible.**
`person.person` and `person.businessentity` are empty. `sales.customer` records exist (19,820 rows) but cannot be joined to names. The lifecycle trace sample order #51131 shows `customer_name: null` for this reason.

**B2B account detail is unavailable.**
`sales.store` is empty. The 701 store-type customers exist in `sales.customer` (via `storeid`) but their names, demographics, and sales rep assignments cannot be resolved.

**Identity layer (person schema) is non-functional.**
Address data exists (19,614 rows in `person.address`) but the linkage tables (`businessentityaddress`, `businessentitycontact`) are empty, making it impossible to associate addresses with specific people or organizations.

---

## Data quality flags

**Planned vs actual production cost are always identical.**
`workorderrouting.actualcost` equals `workorderrouting.plannedcost` exactly across all 67,131 records ($51.96 avg both). Production cost variance is invisible — either the system does not capture actuals, or actuals auto-populate from planned values. Do not use this table for cost variance analysis.

**Sales state machine is frozen at terminal state.**
All 31,465 sales orders have `status = 5` (Shipped). There are no in-flight orders in `salesorderheader`. The table is a historical snapshot, not a live operational view. For real-time monitoring, use `purchasing.purchaseorderheader` (237 active POs) and `production.workorderrouting`.

**Workforce data has no post-2013 hires.**
`humanresources.employee.hiredate` range is Jun 2006 – May 2013. No employee was hired after May 2013 in this dataset. This may reflect the dataset being a historical snapshot rather than the current operational state.

**Credit card expiry years are all in the past.**
`sales.creditcard.expyear` range is 2005–2008. All cards are expired. This is a sample dataset artifact, not a business concern for operational queries.

**Shopping cart has only 3 items.**
`sales.shoppingcartitem` has 3 rows (products 862, 875, 881 added 2024-11-08). No meaningful e-commerce funnel or cart abandonment analysis is possible.

---

## Tables with significant null rates

| Table | Column | Null % | Note |
|---|---|---|---|
| `sales.salesorderheader` | `salespersonid` | 87.9% | Online orders have no rep assigned |
| `sales.salesorderheader` | `purchaseordernumber` | 87.9% | Only B2B orders have a PO number |
| `sales.salesorderheader` | `currencyrateid` | 55.6% | Domestic (USD) orders have no rate |
| `sales.salesorderheader` | `comment` | 100% | No order comments exist |
| `sales.salesorderdetail` | `carriertrackingnumber` | 49.8% | ~Half of lines have no tracking number |
| `production.product` | `color` | 49.2% | Components/raw materials have no color |
| `production.product` | `discontinueddate` | 100% | No products are discontinued |
| `production.workorder` | `scrapreasonid` | 99.0% | Only 1% of WOs have scrap |
| `purchasing.productvendor` | `onorderqty` | 66.3% | Most products have no quantity on order |
| `humanresources.employeedepartmenthistory` | `enddate` | 98.0% | 98% of dept assignments are still active |
