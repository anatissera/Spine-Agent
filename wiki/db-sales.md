# Sales Schema — Database Reference

**Purpose:** Order management, customer relationships, territory assignment, promotions, payment, currency.

---

## Tables

### `sales.salesorderheader` — 31,465 rows — Spine carrier

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `salesorderid` | integer | NOT NULL | PK. Range 43,659–75,123 |
| `revisionnumber` | smallint | NOT NULL | 2 distinct values (10, 11) |
| `orderdate` | timestamp | NOT NULL | Range: 2022-05-30 → 2025-06-29 |
| `duedate` | timestamp | NOT NULL | Range: 2022-06-11 → 2025-07-11 |
| `shipdate` | timestamp | nullable | Range: 2022-06-06 → 2025-07-06 |
| `status` | smallint | NOT NULL | All = 5 (Shipped). See state-machines.md |
| `onlineorderflag` | boolean | NOT NULL | True = online, False = rep-driven |
| `salesordernumber` | character varying | NOT NULL | — |
| `purchaseordernumber` | character varying | nullable | 87.9% null. Non-null = B2B order |
| `accountnumber` | character varying | nullable | — |
| `customerid` | integer | NOT NULL | FK → sales.customer. Range 11,000–30,118 |
| `salespersonid` | integer | nullable | 87.9% null. FK → sales.salesperson. Range 274–290 |
| `territoryid` | integer | NOT NULL | FK → sales.salesterritory. 10 distinct |
| `billtoaddressid` | integer | NOT NULL | Range 405–29,883 |
| `shiptoaddressid` | integer | NOT NULL | Range 9–29,883 |
| `shipmethodid` | integer | NOT NULL | 2 distinct values (1, 5) |
| `creditcardid` | integer | nullable | 3.6% null. FK → sales.creditcard |
| `creditcardapprovalcode` | character varying | nullable | — |
| `currencyrateid` | integer | nullable | 55.6% null. FK → sales.currencyrate |
| `subtotal` | numeric | NOT NULL | Range: $1.37 – $163,930. Avg: $3,491 |
| `taxamt` | numeric | NOT NULL | Range: $0.11 – $17,949. Avg: $324 |
| `freight` | numeric | NOT NULL | Range: $0.03 – $5,609. Avg: $101 |
| `totaldue` | numeric | computed | Range: $1.52 – $187,488. Avg: $3,916 |
| `comment` | character varying | nullable | 100% null |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | Range: 2022-06-06 → 2025-07-06 |

**FK outbound:** customerid → sales.customer | salespersonid → sales.salesperson | territoryid → sales.salesterritory | creditcardid → sales.creditcard | currencyrateid → sales.currencyrate

**FK inbound:** salesorderdetail.salesorderid | salesorderheadersalesreason.salesorderid

---

### `sales.salesorderdetail` — 121,317 rows — Spine line items

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `salesorderid` | integer | NOT NULL | FK → salesorderheader. 31,465 distinct orders |
| `salesorderdetailid` | integer | NOT NULL | PK |
| `carriertrackingnumber` | character varying | nullable | 49.8% null. 3,806 distinct values |
| `orderqty` | smallint | NOT NULL | Range: 1–44. Avg: 2.27 |
| `productid` | integer | NOT NULL | FK → specialofferproduct. 266 distinct (range 707–999) |
| `specialofferid` | integer | NOT NULL | FK → specialofferproduct. 12 distinct |
| `unitprice` | numeric | NOT NULL | Range: $1.33 – $3,578.27. Avg: $465 |
| `unitpricediscount` | numeric | NOT NULL | Range: 0.0 – 0.40. Avg: 0.00 (mostly 0) |
| `linetotal` | numeric | computed | — |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | Range: 2022-05-30 → 2025-06-29 |

---

### `sales.customer` — 19,820 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `customerid` | integer | NOT NULL | PK. Range 1–30,118 |
| `personid` | integer | nullable | 3.5% null. Links to person.person (empty) |
| `storeid` | integer | nullable | 93.3% null. 701 B2B store accounts. FK → sales.store (empty) |
| `territoryid` | integer | nullable | FK → salesterritory. 10 distinct |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `sales.salesperson` — 17 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `businessentityid` | integer | NOT NULL | PK. Range 274–290 |
| `territoryid` | integer | nullable | 17.6% null (3 unassigned). FK → salesterritory |
| `salesquota` | numeric | nullable | 17.6% null. Values: $250,000 or $300,000 |
| `bonus` | numeric | NOT NULL | Range: $0 – $6,700. Avg: $2,860 |
| `commissionpct` | numeric | NOT NULL | Range: 0.00 – 0.02. Avg: 0.01 |
| `salesytd` | numeric | NOT NULL | Range: $172,524 – $4,251,369. Avg: $2,133,976 |
| `saleslastyear` | numeric | NOT NULL | Range: $0 – $2,396,540 |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | Range: 2021-12-27 → 2024-05-22 |

---

### `sales.salesterritory` — 10 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `territoryid` | integer | NOT NULL | PK. Range 1–10 |
| `name` | character varying | NOT NULL | 10 distinct territory names |
| `countryregioncode` | character varying | NOT NULL | 6 distinct country codes |
| `group` | character varying | NOT NULL | 3 distinct regional groups |
| `salesytd` | numeric | NOT NULL | Range: $2.4M – $10.5M. Avg: $5.3M |
| `saleslastyear` | numeric | NOT NULL | Range: $1.3M – $5.7M. Avg: $3.3M |
| `costytd` | numeric | NOT NULL | All = 0 |
| `costlastyear` | numeric | NOT NULL | All = 0 |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `sales.salespersonquotahistory` — 163 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `businessentityid` | integer | NOT NULL | FK → salesperson. 17 distinct |
| `quotadate` | timestamp | NOT NULL | 12 distinct dates: 2022-05-30 → 2025-02-28 |
| `salesquota` | numeric | NOT NULL | Range: $1,000 – $1,898,000. Avg: $587,202 |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `sales.salesterritoryhistory` — 17 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `businessentityid` | integer | NOT NULL | FK → salesperson. 14 distinct |
| `territoryid` | integer | NOT NULL | FK → salesterritory |
| `startdate` | timestamp | NOT NULL | 5 distinct: 2022-05-30 → 2024-05-29 |
| `enddate` | timestamp | nullable | 76.5% null (active assignments) |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `sales.creditcard` — 19,118 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `creditcardid` | integer | NOT NULL | PK. Range 1–19,237 |
| `cardtype` | character varying | NOT NULL | SuperiorCard (4,839), Distinguish (4,832), ColonialVoice (4,782), Vista (4,665) |
| `cardnumber` | character varying | NOT NULL | — |
| `expmonth` | smallint | NOT NULL | Range 1–12 |
| `expyear` | smallint | NOT NULL | Range 2005–2008 ⚠️ all expired |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `sales.personcreditcard` — 19,118 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `businessentityid` | integer | NOT NULL | Range 293–20,777. Links to person (empty) |
| `creditcardid` | integer | NOT NULL | FK → creditcard |
| `modifieddate` | timestamp | NOT NULL | Range: 2022-05-30 → 2025-06-29 |

---

### `sales.currencyrate` — 13,532 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `currencyrateid` | integer | NOT NULL | PK |
| `currencyratedate` | timestamp | NOT NULL | Range: 2022-05-30 → 2025-05-30 |
| `fromcurrencycode` | character | NOT NULL | FK → currency |
| `tocurrencycode` | character | NOT NULL | FK → currency |
| `averagerate` | numeric | NOT NULL | Range: 0.60 – 1,500.00 |
| `endofdayrate` | numeric | NOT NULL | Range: 0.60 – 1,499.95 |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `sales.salesorderheadersalesreason` — 27,647 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `salesorderid` | integer | NOT NULL | FK → salesorderheader. 23,012 distinct orders |
| `salesreasonid` | integer | NOT NULL | FK → salesreason. 7 distinct (range 1–10) |
| `modifieddate` | timestamp | NOT NULL | — |

Top reasons: 1→17,473 | 2→3,515 | 5→1,746 | 9→1,551 | 10→1,395 | 6→1,245 | 4→722

---

### `sales.salesreason` — 10 rows

| Column | Type | Nullable |
|---|---|---|
| `salesreasonid` | integer | NOT NULL |
| `name` | character varying | NOT NULL |
| `reasontype` | character varying | NOT NULL |
| `modifieddate` | timestamp | NOT NULL |

Reason types: Other (5), Marketing (4), Promotion (1)

---

### `sales.specialoffer` — 16 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `specialofferid` | integer | NOT NULL | PK |
| `description` | character varying | NOT NULL | — |
| `discountpct` | numeric | NOT NULL | Range: 0% – 50%. Avg: 22% |
| `type` | character varying | NOT NULL | See state-machines.md |
| `category` | character varying | NOT NULL | — |
| `startdate` | timestamp | NOT NULL | Range: 2022-04-30 → 2025-03-30 |
| `enddate` | timestamp | NOT NULL | Range: 2023-05-29 → 2025-11-29 |
| `minqty` | integer | NOT NULL | Range: 0–61 |
| `maxqty` | integer | nullable | 75% null. Range: 14–60 |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `sales.specialofferproduct` — 538 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `specialofferid` | integer | NOT NULL | FK → specialoffer. 15 distinct |
| `productid` | integer | NOT NULL | 295 distinct products (range 680–999) |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `sales.currency` — 105 rows | `sales.countryregioncurrency` — 109 rows | `sales.salestaxrate` — 29 rows | `sales.shoppingcartitem` — 3 rows

`salestaxrate`: taxrate range 5.0%–19.6%, avg 9.1%. 3 tax types.
`shoppingcartitem`: 3 items (productids 862, 875, 881), added 2024-11-08.

---

## Foreign keys (intra-schema only)

```
salesorderdetail.salesorderid → salesorderheader.salesorderid
salesorderdetail.productid → specialofferproduct.productid
salesorderdetail.specialofferid → specialofferproduct.specialofferid
salesorderheader.creditcardid → creditcard.creditcardid
salesorderheader.currencyrateid → currencyrate.currencyrateid
salesorderheader.customerid → customer.customerid
salesorderheader.salespersonid → salesperson.businessentityid
salesorderheader.territoryid → salesterritory.territoryid
salesorderheadersalesreason.salesorderid → salesorderheader.salesorderid
salesorderheadersalesreason.salesreasonid → salesreason.salesreasonid
salesperson.territoryid → salesterritory.territoryid
salespersonquotahistory.businessentityid → salesperson.businessentityid
salesterritoryhistory.businessentityid → salesperson.businessentityid
salesterritoryhistory.territoryid → salesterritory.territoryid
specialofferproduct.specialofferid → specialoffer.specialofferid
store.salespersonid → salesperson.businessentityid
personcreditcard.creditcardid → creditcard.creditcardid
customer.territoryid → salesterritory.territoryid
currencyrate.fromcurrencycode → currency.currencycode
currencyrate.tocurrencycode → currency.currencycode
countryregioncurrency.currencycode → currency.currencycode
```

No cross-schema FKs declared. To join sales data to production or purchasing, join on `productid` by convention.
