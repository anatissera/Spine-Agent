# Person Schema — Database Reference

**Purpose:** Universal identity layer. Resolves people, organizations, addresses, and contact information across all domains using `businessentityid` as the universal key.

⚠️ **Most tables in this schema are empty in the current dataset.** Only `address`, `stateprovince`, `countryregion`, `addresstype`, `contacttype`, and `phonenumbertype` have data. See [data-quality.md](data-quality.md).

---

## Tables with data

### `person.address` — 19,614 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `addressid` | integer | NOT NULL | PK. Range 1–32,521 |
| `addressline1` | character varying | NOT NULL | — |
| `addressline2` | character varying | nullable | 98.2% null |
| `city` | character varying | NOT NULL | — |
| `stateprovinceid` | integer | NOT NULL | FK → stateprovince. 74 distinct |
| `postalcode` | character varying | NOT NULL | — |
| `spatiallocation` | geography | nullable | — |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | Range: 2017-06-22 → 2025-06-29 |

**Note:** `person.businessentityaddress` is empty, so addresses cannot be linked to specific people or organizations.

Top state provinces by address count: 9 (4,564), 79 (2,636), 14 (1,954), 50 (1,588), 7 (1,579).

---

### `person.stateprovince` — 181 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `stateprovinceid` | integer | NOT NULL | PK. Range 1–181 |
| `stateprovincecode` | character | NOT NULL | 181 distinct codes |
| `countryregioncode` | character varying | NOT NULL | FK → countryregion |
| `isonlystateprovinceflag` | boolean | NOT NULL | — |
| `name` | character varying | NOT NULL | — |
| `territoryid` | integer | NOT NULL | FK → sales.salesterritory (by convention). 10 distinct |
| `rowguid` | uuid | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `person.countryregion` — 238 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `countryregioncode` | character varying | NOT NULL | PK |
| `name` | character varying | NOT NULL | 238 distinct country names |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `person.addresstype` — 6 rows

6 address type definitions (IDs 1–6). Used by `businessentityaddress` (empty).

### `person.contacttype` — 20 rows

20 contact type definitions (IDs 1–20). Used by `businessentitycontact` (empty).

### `person.phonenumbertype` — 0 rows

Phone number type lookup — empty.

---

## Empty tables

| Table | Expected content |
|---|---|
| `person.businessentity` | Root entity record for all persons and orgs |
| `person.businessentityaddress` | Links entities to addresses |
| `person.businessentitycontact` | Links entities to contact persons |
| `person.emailaddress` | Email addresses |
| `person.password` | Login credentials |
| `person.person` | Person master (name, type, demographics) |
| `person.personphone` | Phone numbers |
| `person.phonenumbertype` | Phone type lookup |
| `person.vadditionalcontactinfo` | Additional contact info view |

---

## Foreign keys (intra-schema)

```
address.stateprovinceid → stateprovince.stateprovinceid
businessentityaddress.addressid → address.addressid
businessentityaddress.addresstypeid → addresstype.addresstypeid
businessentityaddress.businessentityid → businessentity.businessentityid
businessentitycontact.businessentityid → businessentity.businessentityid
businessentitycontact.contacttypeid → contacttype.contacttypeid
businessentitycontact.personid → person.businessentityid
emailaddress.businessentityid → person.businessentityid
password.businessentityid → person.businessentityid
person.businessentityid → businessentity.businessentityid
personphone.businessentityid → person.businessentityid
personphone.phonenumbertypeid → phonenumbertype.phonenumbertypeid
stateprovince.countryregioncode → countryregion.countryregioncode
```

---

## Cross-domain identity resolution

`businessentityid` is the universal identity key across all domains:

| Domain | Table | businessentityid refers to |
|---|---|---|
| `humanresources` | employee | An employee |
| `purchasing` | vendor | A vendor/supplier organization |
| `purchasing` | productvendor | A vendor (same range 1,492–1,698) |
| `sales` | salesperson | A sales rep (range 274–290) |
| `sales` | personcreditcard | A customer person |
| `person` | person | Any person (empty) |
| `person` | businessentity | Any entity (empty) |

To resolve vendor names: `purchasing.vendor.name` (available).
To resolve employee names: not possible — `person.person` is empty.
To resolve customer names: not possible — `person.person` is empty.
