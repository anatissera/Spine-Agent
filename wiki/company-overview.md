# Company Overview — Adventure Works Cycles

## What they make

Adventure Works Cycles is a bicycle manufacturer. Products span four categories with 37 subcategories:

- **Bikes** — fully assembled bicycles (touring, road, mountain)
- **Components** — frames, saddles, pedals, forks, handlebars, wheels, etc.
- **Clothing** — cycling apparel
- **Accessories** — helmets, pumps, locks, etc.

Product naming convention: **HL** = High-end, **ML** = Mid-line, **LL** = Low-end.
Example products from operational data: HL Touring Frame (Blue/Yellow), LL Touring Frame, Touring Pedal, HL/ML/LL Touring Seat-Saddle.

The catalog has 504 total SKUs: ~59% are catalog/finished goods (with subcategory), ~41% are raw materials and internal components (no subcategory, used in manufacturing only).

## Business scale

| Attribute | Value |
|---|---|
| Data period | May 2022 – June 2025 (37 months) |
| Annualized revenue (est.) | ~$40M / year |
| Gross margin | ~42% |
| Total orders (period) | 31,465 |
| Total order line items | 121,317 |
| Active customers | 19,820 |
| B2B store accounts | 701 |
| Employees | 290 |
| Departments | 16 (across 6 groups) |
| Vendors | 104 (86 active) |
| Sales reps | 17 (across 10 territories) |
| Product SKUs | 504 |
| Manufacturing locations | 14 |
| Avg order value | $3,916 (totaldue) |

## Sales channels

| Channel | Orders | Share |
|---|---|---|
| Online (direct-to-consumer) | ~27,658 | 87.9% |
| B2B / sales rep managed | ~3,807 | 12.1% |

B2B orders are identified by a non-null `purchaseordernumber` and assigned `salespersonid` on `salesorderheader`.

Individual consumers: 19,119 (96.5% of customers). Store/business accounts: 701 (3.5%).

## Geographic reach

- 10 sales territories across 3 regional groups
- 44.4% of sales orders are in foreign currencies (non-USD)
- Addresses cover 74 distinct state/provinces across 238 countries/regions

## Operational domains

| Domain | Schema | Business function |
|---|---|---|
| Sales | `sales` | Order creation, customer management, territory assignment, promotions, credit |
| Production | `production` | Manufacturing (work orders + routing), product catalog, BOM, inventory, event log |
| Purchasing | `purchasing` | Procurement (purchase orders), vendor management, component sourcing |
| Human Resources | `humanresources` | Employees, departments, pay rates, shifts, org hierarchy |
| Identity | `person` | Universal identity layer — resolves people, addresses, and contacts across all domains |

## Integration architecture

The three operational domains (Sales, Production, Purchasing) share **no declared foreign key constraints** across schemas. All 65 FK constraints are intra-schema. Cross-domain relationships are enforced by application convention:

- `productid` links sales orders → work orders → purchase orders (production ↔ purchasing ↔ sales)
- `businessentityid` links employees, vendors, and salespeople to their person records (all domains)

The operational spine exists in the data but is implicit — no existing system makes it explicit. See [spine.md](spine.md).

## Data limitations

Several important tables are empty in this dataset (person, businessentity, store, emailaddress).
This means customer names and B2B account details cannot be resolved.
See [data-quality.md](data-quality.md) for the full list.
