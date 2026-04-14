# Human Resources Schema — Database Reference

**Purpose:** Employee management, department assignments, pay history, work shifts, and org hierarchy.

---

## Tables

### `humanresources.employee` — 290 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `businessentityid` | integer | NOT NULL | PK. Range 1–290. **Links to person schema via businessentityid** |
| `nationalidnumber` | character varying | NOT NULL | — |
| `loginid` | character varying | NOT NULL | — |
| `jobtitle` | character varying | NOT NULL | 67 distinct job titles |
| `birthdate` | date | NOT NULL | Range: 1951-10-17 → 1991-05-31 |
| `maritalstatus` | character | NOT NULL | M (Married) = 146, S (Single) = 144 |
| `gender` | character | NOT NULL | 2 distinct values |
| `hiredate` | date | NOT NULL | Range: 2006-06-30 → 2013-05-30 |
| `salariedflag` | boolean | NOT NULL | Salaried vs hourly |
| `vacationhours` | smallint | NOT NULL | Range: 0–99. Avg: 50.6 |
| `sickleavehours` | smallint | NOT NULL | Range: 20–80. Avg: 45.3 |
| `currentflag` | boolean | NOT NULL | All = true (all employees are current) |
| `rowguid` | uuid | NOT NULL | — |
| `organizationnode` | character varying | NOT NULL | 290 distinct org tree positions |
| `organizationlevel` | integer | nullable | Derived from organizationnode |
| `modifieddate` | timestamp | NOT NULL | Range: 2014-06-30 → 2014-12-26 |

Note: No hires after May 2013 — dataset may be a historical snapshot. See [data-quality.md](data-quality.md).

---

### `humanresources.employeedepartmenthistory` — 296 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `businessentityid` | integer | NOT NULL | FK → employee. 290 distinct |
| `departmentid` | smallint | NOT NULL | FK → department. 16 distinct |
| `shiftid` | smallint | NOT NULL | FK → shift. Range 1–3. Avg: 1.56 |
| `startdate` | date | NOT NULL | Range: 2006-06-30 → 2013-11-14 |
| `enddate` | date | nullable | 98.0% null (almost all assignments still active). Range: 2009-07-14 → 2013-11-13 |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `humanresources.employeepayhistory` — 316 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `businessentityid` | integer | NOT NULL | FK → employee. 290 distinct (avg 1.09 records/employee) |
| `ratechangedate` | timestamp | NOT NULL | Range: 2006-06-30 → 2013-07-14 |
| `rate` | numeric | NOT NULL | Range: $6.50 – $125.50 / hr. Avg: $17.76 |
| `payfrequency` | smallint | NOT NULL | 1 = monthly, 2 = biweekly. Avg: 1.43 (majority biweekly) |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `humanresources.department` — 16 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `departmentid` | integer | NOT NULL | PK. Range 1–16 |
| `name` | character varying | NOT NULL | 16 distinct department names |
| `groupname` | character varying | NOT NULL | 6 distinct group names |
| `modifieddate` | timestamp | NOT NULL | — |

---

### `humanresources.shift` — 3 rows

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `shiftid` | integer | NOT NULL | PK. Range 1–3 |
| `name` | character varying | NOT NULL | 3 shift names |
| `starttime` | time | NOT NULL | — |
| `endtime` | time | NOT NULL | — |
| `modifieddate` | timestamp | NOT NULL | — |

---

### Empty tables

`humanresources.jobcandidate` — 0 rows. No talent pipeline data.

All views (`vemployee`, `vemployeedepartment`, `vemployeedepartmenthistory`, `vjobcandidate`, `vjobcandidateeducation`, `vjobcandidateemployment`) return 0 rows because they depend on `person.person` which is empty.

---

## Foreign keys (intra-schema only)

```
employeedepartmenthistory.businessentityid → employee.businessentityid
employeedepartmenthistory.departmentid → department.departmentid
employeedepartmenthistory.shiftid → shift.shiftid
employeepayhistory.businessentityid → employee.businessentityid
jobcandidate.businessentityid → employee.businessentityid
```

**Cross-domain joins (by convention):**
- `employee.businessentityid = sales.salesperson.businessentityid` — resolves which employees are sales reps
- `purchaseorderheader.employeeid` references employee.businessentityid (range 250–261) — the 12 buyers
- `employee.businessentityid = person.person.businessentityid` — would resolve names (person table is empty)

---

## Key operational queries

**Find which employees place purchase orders:**
```sql
SELECT DISTINCT poh.employeeid, e.jobtitle
FROM purchasing.purchaseorderheader poh
JOIN humanresources.employee e ON e.businessentityid = poh.employeeid
ORDER BY poh.employeeid;
```

**Employee department assignments (current):**
```sql
SELECT e.businessentityid, e.jobtitle, d.name AS department, d.groupname
FROM humanresources.employee e
JOIN humanresources.employeedepartmenthistory edh ON edh.businessentityid = e.businessentityid
JOIN humanresources.department d ON d.departmentid = edh.departmentid
WHERE edh.enddate IS NULL;
```

**Pay rate by employee:**
```sql
SELECT e.businessentityid, e.jobtitle, eph.rate, eph.payfrequency
FROM humanresources.employee e
JOIN humanresources.employeepayhistory eph ON eph.businessentityid = e.businessentityid
WHERE eph.ratechangedate = (
  SELECT MAX(ratechangedate) FROM humanresources.employeepayhistory
  WHERE businessentityid = e.businessentityid
);
```
