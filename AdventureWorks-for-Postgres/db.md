# AdventureWorks — Operational Spine Analysis
_Generated: 2026-04-14 11:51:57_

## Contents
1. [Schema Map](#1-schema-map)
2. [Row Counts](#2-row-counts)
3. [FK Graph](#3-fk-graph)
4. [Spine Identification](#4-spine-identification)
5. [State Machine Detection](#5-state-machine-detection)
6. [Data Profile](#6-data-profile)
7. [Lifecycle Trace](#7-lifecycle-trace)

---
## 1. Schema Map

### `humanresources`  (12 tables/views)

| Table | Columns |
|-------|---------|
| `department` | `departmentid` *integer*, `name` *character varying*, `groupname` *character varying*, `modifieddate` *timestamp without time zone* |
| `employee` | `businessentityid` *integer*, `nationalidnumber` *character varying*, `loginid` *character varying*, `jobtitle` *character varying*, `birthdate` *date*, `maritalstatus` *character* +9 more |
| `employeedepartmenthistory` | `businessentityid` *integer*, `departmentid` *smallint*, `shiftid` *smallint*, `startdate` *date*, `enddate` *date* ⚠️null, `modifieddate` *timestamp without time zone* |
| `employeepayhistory` | `businessentityid` *integer*, `ratechangedate` *timestamp without time zone*, `rate` *numeric*, `payfrequency` *smallint*, `modifieddate` *timestamp without time zone* |
| `jobcandidate` | `jobcandidateid` *integer*, `businessentityid` *integer* ⚠️null, `resume` *xml* ⚠️null, `modifieddate` *timestamp without time zone* |
| `shift` | `shiftid` *integer*, `name` *character varying*, `starttime` *time without time zone*, `endtime` *time without time zone*, `modifieddate` *timestamp without time zone* |
| `vemployee` | `businessentityid` *integer* ⚠️null, `title` *character varying* ⚠️null, `firstname` *character varying* ⚠️null, `middlename` *character varying* ⚠️null, `lastname` *character varying* ⚠️null, `suffix` *character varying* ⚠️null +12 more |
| `vemployeedepartment` | `businessentityid` *integer* ⚠️null, `title` *character varying* ⚠️null, `firstname` *character varying* ⚠️null, `middlename` *character varying* ⚠️null, `lastname` *character varying* ⚠️null, `suffix` *character varying* ⚠️null +4 more |
| `vemployeedepartmenthistory` | `businessentityid` *integer* ⚠️null, `title` *character varying* ⚠️null, `firstname` *character varying* ⚠️null, `middlename` *character varying* ⚠️null, `lastname` *character varying* ⚠️null, `suffix` *character varying* ⚠️null +5 more |
| `vjobcandidate` | `jobcandidateid` *integer* ⚠️null, `businessentityid` *integer* ⚠️null, `Name.Prefix` *character varying* ⚠️null, `Name.First` *character varying* ⚠️null, `Name.Middle` *character varying* ⚠️null, `Name.Last` *character varying* ⚠️null +10 more |
| `vjobcandidateeducation` | `jobcandidateid` *integer* ⚠️null, `Edu.Level` *character varying* ⚠️null, `Edu.StartDate` *date* ⚠️null, `Edu.EndDate` *date* ⚠️null, `Edu.Degree` *character varying* ⚠️null, `Edu.Major` *character varying* ⚠️null +7 more |
| `vjobcandidateemployment` | `jobcandidateid` *integer* ⚠️null, `Emp.StartDate` *date* ⚠️null, `Emp.EndDate` *date* ⚠️null, `Emp.OrgName` *character varying* ⚠️null, `Emp.JobTitle` *character varying* ⚠️null, `Emp.Responsibility` *character varying* ⚠️null +5 more |

### `person`  (14 tables/views)

| Table | Columns |
|-------|---------|
| `address` | `addressid` *integer*, `addressline1` *character varying*, `addressline2` *character varying* ⚠️null, `city` *character varying*, `stateprovinceid` *integer*, `postalcode` *character varying* +3 more |
| `addresstype` | `addresstypeid` *integer*, `name` *character varying*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `businessentity` | `businessentityid` *integer*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `businessentityaddress` | `businessentityid` *integer*, `addressid` *integer*, `addresstypeid` *integer*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `businessentitycontact` | `businessentityid` *integer*, `personid` *integer*, `contacttypeid` *integer*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `contacttype` | `contacttypeid` *integer*, `name` *character varying*, `modifieddate` *timestamp without time zone* |
| `countryregion` | `countryregioncode` *character varying*, `name` *character varying*, `modifieddate` *timestamp without time zone* |
| `emailaddress` | `businessentityid` *integer*, `emailaddressid` *integer*, `emailaddress` *character varying* ⚠️null, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `password` | `businessentityid` *integer*, `passwordhash` *character varying*, `passwordsalt` *character varying*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `person` | `businessentityid` *integer*, `persontype` *character*, `namestyle` *boolean*, `title` *character varying* ⚠️null, `firstname` *character varying*, `middlename` *character varying* ⚠️null +7 more |
| `personphone` | `businessentityid` *integer*, `phonenumber` *character varying*, `phonenumbertypeid` *integer*, `modifieddate` *timestamp without time zone* |
| `phonenumbertype` | `phonenumbertypeid` *integer*, `name` *character varying*, `modifieddate` *timestamp without time zone* |
| `stateprovince` | `stateprovinceid` *integer*, `stateprovincecode` *character*, `countryregioncode` *character varying*, `isonlystateprovinceflag` *boolean*, `name` *character varying*, `territoryid` *integer* +2 more |
| `vadditionalcontactinfo` | `businessentityid` *integer* ⚠️null, `firstname` *character varying* ⚠️null, `middlename` *character varying* ⚠️null, `lastname` *character varying* ⚠️null, `telephonenumber` *xml* ⚠️null, `telephonespecialinstructions` *text* ⚠️null +11 more |

### `production`  (27 tables/views)

| Table | Columns |
|-------|---------|
| `billofmaterials` | `billofmaterialsid` *integer*, `productassemblyid` *integer* ⚠️null, `componentid` *integer*, `startdate` *timestamp without time zone*, `enddate` *timestamp without time zone* ⚠️null, `unitmeasurecode` *character* +3 more |
| `culture` | `cultureid` *character*, `name` *character varying*, `modifieddate` *timestamp without time zone* |
| `document` | `title` *character varying*, `owner` *integer*, `folderflag` *boolean*, `filename` *character varying*, `fileextension` *character varying* ⚠️null, `revision` *character* +7 more |
| `illustration` | `illustrationid` *integer*, `diagram` *xml* ⚠️null, `modifieddate` *timestamp without time zone* |
| `location` | `locationid` *integer*, `name` *character varying*, `costrate` *numeric*, `availability` *numeric*, `modifieddate` *timestamp without time zone* |
| `product` | `productid` *integer*, `name` *character varying*, `productnumber` *character varying*, `makeflag` *boolean*, `finishedgoodsflag` *boolean*, `color` *character varying* ⚠️null +19 more |
| `productcategory` | `productcategoryid` *integer*, `name` *character varying*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `productcosthistory` | `productid` *integer*, `startdate` *timestamp without time zone*, `enddate` *timestamp without time zone* ⚠️null, `standardcost` *numeric*, `modifieddate` *timestamp without time zone* |
| `productdescription` | `productdescriptionid` *integer*, `description` *character varying*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `productdocument` | `productid` *integer*, `modifieddate` *timestamp without time zone*, `documentnode` *character varying* |
| `productinventory` | `productid` *integer*, `locationid` *smallint*, `shelf` *character varying*, `bin` *smallint*, `quantity` *smallint*, `rowguid` *uuid* +1 more |
| `productlistpricehistory` | `productid` *integer*, `startdate` *timestamp without time zone*, `enddate` *timestamp without time zone* ⚠️null, `listprice` *numeric*, `modifieddate` *timestamp without time zone* |
| `productmodel` | `productmodelid` *integer*, `name` *character varying*, `catalogdescription` *xml* ⚠️null, `instructions` *xml* ⚠️null, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `productmodelillustration` | `productmodelid` *integer*, `illustrationid` *integer*, `modifieddate` *timestamp without time zone* |
| `productmodelproductdescriptionculture` | `productmodelid` *integer*, `productdescriptionid` *integer*, `cultureid` *character*, `modifieddate` *timestamp without time zone* |
| `productphoto` | `productphotoid` *integer*, `thumbnailphoto` *bytea* ⚠️null, `thumbnailphotofilename` *character varying* ⚠️null, `largephoto` *bytea* ⚠️null, `largephotofilename` *character varying* ⚠️null, `modifieddate` *timestamp without time zone* |
| `productproductphoto` | `productid` *integer*, `productphotoid` *integer*, `primary` *boolean*, `modifieddate` *timestamp without time zone* |
| `productreview` | `productreviewid` *integer*, `productid` *integer*, `reviewername` *character varying*, `reviewdate` *timestamp without time zone*, `emailaddress` *character varying*, `rating` *integer* +2 more |
| `productsubcategory` | `productsubcategoryid` *integer*, `productcategoryid` *integer*, `name` *character varying*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `scrapreason` | `scrapreasonid` *integer*, `name` *character varying*, `modifieddate` *timestamp without time zone* |
| `transactionhistory` | `transactionid` *integer*, `productid` *integer*, `referenceorderid` *integer*, `referenceorderlineid` *integer*, `transactiondate` *timestamp without time zone*, `transactiontype` *character* +3 more |
| `transactionhistoryarchive` | `transactionid` *integer*, `productid` *integer*, `referenceorderid` *integer*, `referenceorderlineid` *integer*, `transactiondate` *timestamp without time zone*, `transactiontype` *character* +3 more |
| `unitmeasure` | `unitmeasurecode` *character*, `name` *character varying*, `modifieddate` *timestamp without time zone* |
| `vproductmodelcatalogdescription` | `productmodelid` *integer* ⚠️null, `name` *character varying* ⚠️null, `Summary` *character varying* ⚠️null, `manufacturer` *character varying* ⚠️null, `copyright` *character varying* ⚠️null, `producturl` *character varying* ⚠️null +19 more |
| `vproductmodelinstructions` | `productmodelid` *integer* ⚠️null, `name` *character varying* ⚠️null, `instructions` *character varying* ⚠️null, `LocationID` *integer* ⚠️null, `SetupHours` *numeric* ⚠️null, `MachineHours` *numeric* ⚠️null +5 more |
| `workorder` | `workorderid` *integer*, `productid` *integer*, `orderqty` *integer*, `scrappedqty` *smallint*, `startdate` *timestamp without time zone*, `enddate` *timestamp without time zone* ⚠️null +3 more |
| `workorderrouting` | `workorderid` *integer*, `productid` *integer*, `operationsequence` *smallint*, `locationid` *smallint*, `scheduledstartdate` *timestamp without time zone*, `scheduledenddate` *timestamp without time zone* +6 more |

### `purchasing`  (7 tables/views)

| Table | Columns |
|-------|---------|
| `productvendor` | `productid` *integer*, `businessentityid` *integer*, `averageleadtime` *integer*, `standardprice` *numeric*, `lastreceiptcost` *numeric* ⚠️null, `lastreceiptdate` *timestamp without time zone* ⚠️null +5 more |
| `purchaseorderdetail` | `purchaseorderid` *integer*, `purchaseorderdetailid` *integer*, `duedate` *timestamp without time zone*, `orderqty` *smallint*, `productid` *integer*, `unitprice` *numeric* +3 more |
| `purchaseorderheader` | `purchaseorderid` *integer*, `revisionnumber` *smallint*, `status` *smallint*, `employeeid` *integer*, `vendorid` *integer*, `shipmethodid` *integer* +6 more |
| `shipmethod` | `shipmethodid` *integer*, `name` *character varying*, `shipbase` *numeric*, `shiprate` *numeric*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `vendor` | `businessentityid` *integer*, `accountnumber` *character varying*, `name` *character varying*, `creditrating` *smallint*, `preferredvendorstatus` *boolean*, `activeflag` *boolean* +2 more |
| `vvendorwithaddresses` | `businessentityid` *integer* ⚠️null, `name` *character varying* ⚠️null, `addresstype` *character varying* ⚠️null, `addressline1` *character varying* ⚠️null, `addressline2` *character varying* ⚠️null, `city` *character varying* ⚠️null +3 more |
| `vvendorwithcontacts` | `businessentityid` *integer* ⚠️null, `name` *character varying* ⚠️null, `contacttype` *character varying* ⚠️null, `title` *character varying* ⚠️null, `firstname` *character varying* ⚠️null, `middlename` *character varying* ⚠️null +6 more |

### `sales`  (27 tables/views)

| Table | Columns |
|-------|---------|
| `countryregioncurrency` | `countryregioncode` *character varying*, `currencycode` *character*, `modifieddate` *timestamp without time zone* |
| `creditcard` | `creditcardid` *integer*, `cardtype` *character varying*, `cardnumber` *character varying*, `expmonth` *smallint*, `expyear` *smallint*, `modifieddate` *timestamp without time zone* |
| `currency` | `currencycode` *character*, `name` *character varying*, `modifieddate` *timestamp without time zone* |
| `currencyrate` | `currencyrateid` *integer*, `currencyratedate` *timestamp without time zone*, `fromcurrencycode` *character*, `tocurrencycode` *character*, `averagerate` *numeric*, `endofdayrate` *numeric* +1 more |
| `customer` | `customerid` *integer*, `personid` *integer* ⚠️null, `storeid` *integer* ⚠️null, `territoryid` *integer* ⚠️null, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `personcreditcard` | `businessentityid` *integer*, `creditcardid` *integer*, `modifieddate` *timestamp without time zone* |
| `salesorderdetail` | `salesorderid` *integer*, `salesorderdetailid` *integer*, `carriertrackingnumber` *character varying* ⚠️null, `orderqty` *smallint*, `productid` *integer*, `specialofferid` *integer* +4 more |
| `salesorderheader` | `salesorderid` *integer*, `revisionnumber` *smallint*, `orderdate` *timestamp without time zone*, `duedate` *timestamp without time zone*, `shipdate` *timestamp without time zone* ⚠️null, `status` *smallint* +19 more |
| `salesorderheadersalesreason` | `salesorderid` *integer*, `salesreasonid` *integer*, `modifieddate` *timestamp without time zone* |
| `salesperson` | `businessentityid` *integer*, `territoryid` *integer* ⚠️null, `salesquota` *numeric* ⚠️null, `bonus` *numeric*, `commissionpct` *numeric*, `salesytd` *numeric* +3 more |
| `salespersonquotahistory` | `businessentityid` *integer*, `quotadate` *timestamp without time zone*, `salesquota` *numeric*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `salesreason` | `salesreasonid` *integer*, `name` *character varying*, `reasontype` *character varying*, `modifieddate` *timestamp without time zone* |
| `salestaxrate` | `salestaxrateid` *integer*, `stateprovinceid` *integer*, `taxtype` *smallint*, `taxrate` *numeric*, `name` *character varying*, `rowguid` *uuid* +1 more |
| `salesterritory` | `territoryid` *integer*, `name` *character varying*, `countryregioncode` *character varying*, `group` *character varying*, `salesytd` *numeric*, `saleslastyear` *numeric* +4 more |
| `salesterritoryhistory` | `businessentityid` *integer*, `territoryid` *integer*, `startdate` *timestamp without time zone*, `enddate` *timestamp without time zone* ⚠️null, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `shoppingcartitem` | `shoppingcartitemid` *integer*, `shoppingcartid` *character varying*, `quantity` *integer*, `productid` *integer*, `datecreated` *timestamp without time zone*, `modifieddate` *timestamp without time zone* |
| `specialoffer` | `specialofferid` *integer*, `description` *character varying*, `discountpct` *numeric*, `type` *character varying*, `category` *character varying*, `startdate` *timestamp without time zone* +5 more |
| `specialofferproduct` | `specialofferid` *integer*, `productid` *integer*, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `store` | `businessentityid` *integer*, `name` *character varying*, `salespersonid` *integer* ⚠️null, `demographics` *xml* ⚠️null, `rowguid` *uuid*, `modifieddate` *timestamp without time zone* |
| `vindividualcustomer` | `businessentityid` *integer* ⚠️null, `title` *character varying* ⚠️null, `firstname` *character varying* ⚠️null, `middlename` *character varying* ⚠️null, `lastname` *character varying* ⚠️null, `suffix` *character varying* ⚠️null +12 more |
| `vpersondemographics` | `businessentityid` *integer* ⚠️null, `totalpurchaseytd` *money* ⚠️null, `datefirstpurchase` *date* ⚠️null, `birthdate` *date* ⚠️null, `maritalstatus` *character varying* ⚠️null, `yearlyincome` *character varying* ⚠️null +7 more |
| `vsalesperson` | `businessentityid` *integer* ⚠️null, `title` *character varying* ⚠️null, `firstname` *character varying* ⚠️null, `middlename` *character varying* ⚠️null, `lastname` *character varying* ⚠️null, `suffix` *character varying* ⚠️null +16 more |
| `vsalespersonsalesbyfiscalyears` | `SalesPersonID` *integer* ⚠️null, `FullName` *text* ⚠️null, `JobTitle` *text* ⚠️null, `SalesTerritory` *text* ⚠️null, `2012` *numeric* ⚠️null, `2013` *numeric* ⚠️null +1 more |
| `vsalespersonsalesbyfiscalyearsdata` | `salespersonid` *integer* ⚠️null, `fullname` *text* ⚠️null, `jobtitle` *character varying* ⚠️null, `salesterritory` *character varying* ⚠️null, `salestotal` *numeric* ⚠️null, `fiscalyear` *numeric* ⚠️null |
| `vstorewithaddresses` | `businessentityid` *integer* ⚠️null, `name` *character varying* ⚠️null, `addresstype` *character varying* ⚠️null, `addressline1` *character varying* ⚠️null, `addressline2` *character varying* ⚠️null, `city` *character varying* ⚠️null +3 more |
| `vstorewithcontacts` | `businessentityid` *integer* ⚠️null, `name` *character varying* ⚠️null, `contacttype` *character varying* ⚠️null, `title` *character varying* ⚠️null, `firstname` *character varying* ⚠️null, `middlename` *character varying* ⚠️null +6 more |
| `vstorewithdemographics` | `businessentityid` *integer* ⚠️null, `name` *character varying* ⚠️null, `AnnualSales` *money* ⚠️null, `AnnualRevenue` *money* ⚠️null, `BankName` *character varying* ⚠️null, `BusinessType` *character varying* ⚠️null +6 more |

---
## 2. Row Counts

| Table | Rows |
|-------|-----:|
| `sales.salesorderdetail` | 121,317 |
| `production.transactionhistory` | 113,443 |
| `production.transactionhistoryarchive` | 89,253 |
| `production.workorder` | 72,591 |
| `production.workorderrouting` | 67,131 |
| `sales.salesorderheader` | 31,465 |
| `sales.salesorderheadersalesreason` | 27,647 |
| `sales.customer` | 19,820 |
| `person.address` | 19,614 |
| `sales.creditcard` | 19,118 |
| `sales.personcreditcard` | 19,118 |
| `sales.currencyrate` | 13,532 |
| `purchasing.purchaseorderdetail` | 8,845 |
| `purchasing.purchaseorderheader` | 4,012 |
| `production.billofmaterials` | 2,679 |
| `production.productinventory` | 1,069 |
| `production.productmodelproductdescriptionculture` | 762 |
| `sales.specialofferproduct` | 538 |
| `production.product` | 504 |
| `production.productproductphoto` | 504 |
| `purchasing.productvendor` | 460 |
| `production.productcosthistory` | 395 |
| `production.productlistpricehistory` | 395 |
| `humanresources.employeepayhistory` | 316 |
| `humanresources.employeedepartmenthistory` | 296 |
| `humanresources.employee` | 290 |
| `person.countryregion` | 238 |
| `person.stateprovince` | 181 |
| `sales.salespersonquotahistory` | 163 |
| `sales.countryregioncurrency` | 109 |
| `sales.currency` | 105 |
| `purchasing.vendor` | 104 |
| `production.unitmeasure` | 38 |
| `production.productsubcategory` | 37 |
| `production.productdocument` | 32 |
| `sales.salestaxrate` | 29 |
| `person.contacttype` | 20 |
| `sales.salesperson` | 17 |
| `sales.salesterritoryhistory` | 17 |
| `humanresources.department` | 16 |
| `production.scrapreason` | 16 |
| `sales.specialoffer` | 16 |
| `production.location` | 14 |
| `sales.salesreason` | 10 |
| `sales.salesterritory` | 10 |
| `production.culture` | 8 |
| `production.productmodelillustration` | 7 |
| `person.addresstype` | 6 |
| `purchasing.shipmethod` | 5 |
| `production.productcategory` | 4 |
| `production.productreview` | 4 |
| `humanresources.shift` | 3 |
| `sales.shoppingcartitem` | 3 |
| `humanresources.jobcandidate` | 0 |
| `humanresources.vemployee` | 0 |
| `humanresources.vemployeedepartment` | 0 |
| `humanresources.vemployeedepartmenthistory` | 0 |
| `humanresources.vjobcandidate` | 0 |
| `humanresources.vjobcandidateeducation` | 0 |
| `humanresources.vjobcandidateemployment` | 0 |
| `person.businessentity` | 0 |
| `person.businessentityaddress` | 0 |
| `person.businessentitycontact` | 0 |
| `person.emailaddress` | 0 |
| `person.password` | 0 |
| `person.person` | 0 |
| `person.personphone` | 0 |
| `person.phonenumbertype` | 0 |
| `person.vadditionalcontactinfo` | 0 |
| `production.document` | 0 |
| `production.illustration` | 0 |
| `production.productdescription` | 0 |
| `production.productmodel` | 0 |
| `production.productphoto` | 0 |
| `production.vproductmodelcatalogdescription` | 0 |
| `production.vproductmodelinstructions` | 0 |
| `purchasing.vvendorwithaddresses` | 0 |
| `purchasing.vvendorwithcontacts` | 0 |
| `sales.store` | 0 |
| `sales.vindividualcustomer` | 0 |
| `sales.vpersondemographics` | 0 |
| `sales.vsalesperson` | 0 |
| `sales.vsalespersonsalesbyfiscalyears` | 0 |
| `sales.vsalespersonsalesbyfiscalyearsdata` | 0 |
| `sales.vstorewithaddresses` | 0 |
| `sales.vstorewithcontacts` | 0 |
| `sales.vstorewithdemographics` | 0 |

---
## 3. FK Graph

- **Total FK edges:** 65
- **Cross-schema:** 0
- **Intra-schema:** 65

### All FK edges by source table

**`humanresources.employeedepartmenthistory`**
- `businessentityid` → `humanresources.employee`.`businessentityid`
- `departmentid` → `humanresources.department`.`departmentid`
- `shiftid` → `humanresources.shift`.`shiftid`

**`humanresources.employeepayhistory`**
- `businessentityid` → `humanresources.employee`.`businessentityid`

**`humanresources.jobcandidate`**
- `businessentityid` → `humanresources.employee`.`businessentityid`

**`person.address`**
- `stateprovinceid` → `person.stateprovince`.`stateprovinceid`

**`person.businessentityaddress`**
- `addressid` → `person.address`.`addressid`
- `addresstypeid` → `person.addresstype`.`addresstypeid`
- `businessentityid` → `person.businessentity`.`businessentityid`

**`person.businessentitycontact`**
- `businessentityid` → `person.businessentity`.`businessentityid`
- `contacttypeid` → `person.contacttype`.`contacttypeid`
- `personid` → `person.person`.`businessentityid`

**`person.emailaddress`**
- `businessentityid` → `person.person`.`businessentityid`

**`person.password`**
- `businessentityid` → `person.person`.`businessentityid`

**`person.person`**
- `businessentityid` → `person.businessentity`.`businessentityid`

**`person.personphone`**
- `businessentityid` → `person.person`.`businessentityid`
- `phonenumbertypeid` → `person.phonenumbertype`.`phonenumbertypeid`

**`person.stateprovince`**
- `countryregioncode` → `person.countryregion`.`countryregioncode`

**`production.billofmaterials`**
- `componentid` → `production.product`.`productid`
- `productassemblyid` → `production.product`.`productid`
- `unitmeasurecode` → `production.unitmeasure`.`unitmeasurecode`

**`production.product`**
- `productsubcategoryid` → `production.productsubcategory`.`productsubcategoryid`
- `sizeunitmeasurecode` → `production.unitmeasure`.`unitmeasurecode`
- `weightunitmeasurecode` → `production.unitmeasure`.`unitmeasurecode`

**`production.productcosthistory`**
- `productid` → `production.product`.`productid`

**`production.productdocument`**
- `productid` → `production.product`.`productid`

**`production.productinventory`**
- `locationid` → `production.location`.`locationid`
- `productid` → `production.product`.`productid`

**`production.productlistpricehistory`**
- `productid` → `production.product`.`productid`

**`production.productmodelproductdescriptionculture`**
- `cultureid` → `production.culture`.`cultureid`

**`production.productproductphoto`**
- `productid` → `production.product`.`productid`

**`production.productreview`**
- `productid` → `production.product`.`productid`

**`production.productsubcategory`**
- `productcategoryid` → `production.productcategory`.`productcategoryid`

**`production.transactionhistory`**
- `productid` → `production.product`.`productid`

**`production.workorder`**
- `productid` → `production.product`.`productid`
- `scrapreasonid` → `production.scrapreason`.`scrapreasonid`

**`production.workorderrouting`**
- `locationid` → `production.location`.`locationid`
- `workorderid` → `production.workorder`.`workorderid`

**`purchasing.productvendor`**
- `businessentityid` → `purchasing.vendor`.`businessentityid`

**`purchasing.purchaseorderdetail`**
- `purchaseorderid` → `purchasing.purchaseorderheader`.`purchaseorderid`

**`purchasing.purchaseorderheader`**
- `shipmethodid` → `purchasing.shipmethod`.`shipmethodid`
- `vendorid` → `purchasing.vendor`.`businessentityid`

**`sales.countryregioncurrency`**
- `currencycode` → `sales.currency`.`currencycode`

**`sales.currencyrate`**
- `fromcurrencycode` → `sales.currency`.`currencycode`
- `tocurrencycode` → `sales.currency`.`currencycode`

**`sales.customer`**
- `territoryid` → `sales.salesterritory`.`territoryid`

**`sales.personcreditcard`**
- `creditcardid` → `sales.creditcard`.`creditcardid`

**`sales.salesorderdetail`**
- `productid` → `sales.specialofferproduct`.`productid`
- `productid` → `sales.specialofferproduct`.`specialofferid`
- `salesorderid` → `sales.salesorderheader`.`salesorderid`
- `specialofferid` → `sales.specialofferproduct`.`productid`
- `specialofferid` → `sales.specialofferproduct`.`specialofferid`

**`sales.salesorderheader`**
- `creditcardid` → `sales.creditcard`.`creditcardid`
- `currencyrateid` → `sales.currencyrate`.`currencyrateid`
- `customerid` → `sales.customer`.`customerid`
- `salespersonid` → `sales.salesperson`.`businessentityid`
- `territoryid` → `sales.salesterritory`.`territoryid`

**`sales.salesorderheadersalesreason`**
- `salesorderid` → `sales.salesorderheader`.`salesorderid`
- `salesreasonid` → `sales.salesreason`.`salesreasonid`

**`sales.salesperson`**
- `territoryid` → `sales.salesterritory`.`territoryid`

**`sales.salespersonquotahistory`**
- `businessentityid` → `sales.salesperson`.`businessentityid`

**`sales.salesterritoryhistory`**
- `businessentityid` → `sales.salesperson`.`businessentityid`
- `territoryid` → `sales.salesterritory`.`territoryid`

**`sales.specialofferproduct`**
- `specialofferid` → `sales.specialoffer`.`specialofferid`

**`sales.store`**
- `salespersonid` → `sales.salesperson`.`businessentityid`

---
## 4. Spine Identification

> Tables ranked by number of **distinct schemas** that reference them via FK.
> A high `distinct_schemas` score = stronger spine candidate.

| Table | Referencing Schemas | Distinct Schemas | Inbound FKs | Outbound FKs |
|-------|---------------------|:----------------:|:-----------:|:------------:|
| `production.product` | `production` | 1 | 10 | 3 |
| `sales.specialofferproduct` | `sales` | 1 | 4 | 1 |
| `sales.salesterritory` | `sales` | 1 | 4 | 0 |
| `person.person` | `person` | 1 | 4 | 1 |
| `sales.salesperson` | `sales` | 1 | 4 | 1 |
| `sales.currency` | `sales` | 1 | 3 | 0 |
| `production.unitmeasure` | `production` | 1 | 3 | 0 |
| `humanresources.employee` | `humanresources` | 1 | 3 | 0 |
| `person.businessentity` | `person` | 1 | 3 | 0 |
| `purchasing.vendor` | `purchasing` | 1 | 2 | 0 |
| `sales.creditcard` | `sales` | 1 | 2 | 0 |
| `sales.salesorderheader` | `sales` | 1 | 2 | 5 |
| `production.location` | `production` | 1 | 2 | 0 |
| `production.productsubcategory` | `production` | 1 | 1 | 1 |
| `person.stateprovince` | `person` | 1 | 1 | 1 |
| `person.contacttype` | `person` | 1 | 1 | 0 |
| `humanresources.department` | `humanresources` | 1 | 1 | 0 |
| `sales.customer` | `sales` | 1 | 1 | 1 |
| `sales.currencyrate` | `sales` | 1 | 1 | 2 |
| `person.addresstype` | `person` | 1 | 1 | 0 |
| `person.phonenumbertype` | `person` | 1 | 1 | 0 |
| `sales.salesreason` | `sales` | 1 | 1 | 0 |
| `production.productcategory` | `production` | 1 | 1 | 0 |
| `humanresources.shift` | `humanresources` | 1 | 1 | 0 |
| `production.workorder` | `production` | 1 | 1 | 2 |
| `production.scrapreason` | `production` | 1 | 1 | 0 |
| `purchasing.shipmethod` | `purchasing` | 1 | 1 | 0 |
| `sales.specialoffer` | `sales` | 1 | 1 | 0 |
| `production.culture` | `production` | 1 | 1 | 0 |
| `person.countryregion` | `person` | 1 | 1 | 0 |
| `person.address` | `person` | 1 | 1 | 1 |
| `purchasing.purchaseorderheader` | `purchasing` | 1 | 1 | 2 |
| `production.productinventory` | — | 0 | 0 | 2 |
| `humanresources.employeepayhistory` | — | 0 | 0 | 1 |
| `sales.salespersonquotahistory` | — | 0 | 0 | 1 |
| `person.password` | — | 0 | 0 | 1 |
| `production.workorderrouting` | — | 0 | 0 | 2 |
| `production.productdocument` | — | 0 | 0 | 1 |
| `sales.salesterritoryhistory` | — | 0 | 0 | 2 |
| `person.emailaddress` | — | 0 | 0 | 1 |
| `production.productreview` | — | 0 | 0 | 1 |
| `sales.salesorderheadersalesreason` | — | 0 | 0 | 2 |
| `purchasing.purchaseorderdetail` | — | 0 | 0 | 1 |
| `person.personphone` | — | 0 | 0 | 2 |
| `purchasing.productvendor` | — | 0 | 0 | 1 |
| `production.productcosthistory` | — | 0 | 0 | 1 |
| `humanresources.jobcandidate` | — | 0 | 0 | 1 |
| `production.transactionhistory` | — | 0 | 0 | 1 |
| `sales.personcreditcard` | — | 0 | 0 | 1 |
| `person.businessentityaddress` | — | 0 | 0 | 3 |
| `sales.countryregioncurrency` | — | 0 | 0 | 1 |
| `production.productlistpricehistory` | — | 0 | 0 | 1 |
| `humanresources.employeedepartmenthistory` | — | 0 | 0 | 3 |
| `production.productproductphoto` | — | 0 | 0 | 1 |
| `production.productmodelproductdescriptionculture` | — | 0 | 0 | 1 |
| `person.businessentitycontact` | — | 0 | 0 | 3 |
| `sales.salesorderdetail` | — | 0 | 0 | 5 |
| `sales.store` | — | 0 | 0 | 1 |
| `production.billofmaterials` | — | 0 | 0 | 3 |

---
## 5. State Machine Detection

Columns whose name contains `status`, `type`, `flag`, `state`, `reason`, `level`, or `class`.

### `humanresources.employee`.`maritalstatus` _character_

| Value | Count |
|-------|------:|
| `M` | 146 |
| `S` | 144 |

### `person.address`.`stateprovinceid` _integer_

| Value | Count |
|-------|------:|
| `9` | 4,564 |
| `79` | 2,636 |
| `14` | 1,954 |
| `50` | 1,588 |
| `7` | 1,579 |
| `58` | 1,105 |
| `77` | 901 |
| `64` | 795 |
| `70` | 453 |
| `53` | 412 |
| `161` | 398 |
| `19` | 385 |
| `20` | 308 |
| `179` | 288 |
| `145` | 286 |
| `66` | 242 |
| `8` | 231 |
| `178` | 201 |
| `164` | 168 |
| `177` | 156 |

### `person.addresstype`.`addresstypeid` _integer_

| Value | Count |
|-------|------:|
| `6` | 1 |
| `1` | 1 |
| `3` | 1 |
| `5` | 1 |
| `4` | 1 |
| `2` | 1 |

### `person.contacttype`.`contacttypeid` _integer_

| Value | Count |
|-------|------:|
| `11` | 1 |
| `8` | 1 |
| `19` | 1 |
| `4` | 1 |
| `14` | 1 |
| `3` | 1 |
| `17` | 1 |
| `20` | 1 |
| `13` | 1 |
| `10` | 1 |
| `9` | 1 |
| `7` | 1 |
| `1` | 1 |
| `5` | 1 |
| `18` | 1 |
| `2` | 1 |
| `16` | 1 |
| `15` | 1 |
| `6` | 1 |
| `12` | 1 |

### `person.stateprovince`.`stateprovinceid` _integer_

| Value | Count |
|-------|------:|
| `87` | 1 |
| `71` | 1 |
| `68` | 1 |
| `51` | 1 |
| `146` | 1 |
| `80` | 1 |
| `70` | 1 |
| `52` | 1 |
| `162` | 1 |
| `132` | 1 |
| `84` | 1 |
| `170` | 1 |
| `176` | 1 |
| `169` | 1 |
| `92` | 1 |
| `101` | 1 |
| `69` | 1 |
| `180` | 1 |
| `115` | 1 |
| `116` | 1 |

### `person.stateprovince`.`stateprovincecode` _character_

| Value | Count |
|-------|------:|
| `75 ` | 1 |
| `13 ` | 1 |
| `SN ` | 1 |
| `93 ` | 1 |
| `NV ` | 1 |
| `94 ` | 1 |
| `OH ` | 1 |
| `95 ` | 1 |
| `34 ` | 1 |
| `NY ` | 1 |
| `MH ` | 1 |
| `NS ` | 1 |
| `18 ` | 1 |
| `32 ` | 1 |
| `QC ` | 1 |
| `BC ` | 1 |
| `NW ` | 1 |
| `76 ` | 1 |
| `WV ` | 1 |
| `KS ` | 1 |

### `production.billofmaterials`.`bomlevel` _smallint_

| Value | Count |
|-------|------:|
| `1` | 1,548 |
| `2` | 993 |
| `0` | 103 |
| `3` | 31 |
| `4` | 4 |

### `production.product`.`safetystocklevel` _smallint_

| Value | Count |
|-------|------:|
| `500` | 167 |
| `1000` | 156 |
| `100` | 97 |
| `4` | 54 |
| `800` | 25 |
| `60` | 5 |

### `production.product`.`class` _character_

| Value | Count |
|-------|------:|
| `None` | 257 |
| `L ` | 97 |
| `H ` | 82 |
| `M ` | 68 |

### `production.scrapreason`.`scrapreasonid` _integer_

| Value | Count |
|-------|------:|
| `4` | 1 |
| `14` | 1 |
| `3` | 1 |
| `13` | 1 |
| `10` | 1 |
| `9` | 1 |
| `7` | 1 |
| `1` | 1 |
| `5` | 1 |
| `2` | 1 |
| `16` | 1 |
| `15` | 1 |
| `6` | 1 |
| `12` | 1 |
| `11` | 1 |
| `8` | 1 |

### `production.transactionhistory`.`transactiontype` _character_

| Value | Count |
|-------|------:|
| `S` | 74,575 |
| `W` | 31,002 |
| `P` | 7,866 |

### `production.transactionhistoryarchive`.`transactiontype` _character_

| Value | Count |
|-------|------:|
| `S` | 46,742 |
| `W` | 41,589 |
| `P` | 922 |

### `production.workorder`.`scrapreasonid` _smallint_

| Value | Count |
|-------|------:|
| `None` | 71,862 |
| `13` | 63 |
| `3` | 54 |
| `11` | 52 |
| `14` | 52 |
| `16` | 51 |
| `15` | 48 |
| `9` | 47 |
| `4` | 45 |
| `6` | 44 |
| `1` | 44 |
| `2` | 44 |
| `5` | 42 |
| `12` | 37 |
| `10` | 37 |
| `8` | 37 |
| `7` | 32 |

### `purchasing.purchaseorderheader`.`status` _smallint_

| Value | Count |
|-------|------:|
| `4` | 3,689 |
| `1` | 225 |
| `3` | 86 |
| `2` | 12 |

### `sales.creditcard`.`cardtype` _character varying_

| Value | Count |
|-------|------:|
| `SuperiorCard` | 4,839 |
| `Distinguish` | 4,832 |
| `ColonialVoice` | 4,782 |
| `Vista` | 4,665 |

### `sales.salesorderheader`.`status` _smallint_

| Value | Count |
|-------|------:|
| `5` | 31,465 |

### `sales.salesorderheadersalesreason`.`salesreasonid` _integer_

| Value | Count |
|-------|------:|
| `1` | 17,473 |
| `2` | 3,515 |
| `5` | 1,746 |
| `9` | 1,551 |
| `10` | 1,395 |
| `6` | 1,245 |
| `4` | 722 |

### `sales.salesreason`.`salesreasonid` _integer_

| Value | Count |
|-------|------:|
| `8` | 1 |
| `10` | 1 |
| `9` | 1 |
| `7` | 1 |
| `1` | 1 |
| `5` | 1 |
| `4` | 1 |
| `2` | 1 |
| `6` | 1 |
| `3` | 1 |

### `sales.salesreason`.`reasontype` _character varying_

| Value | Count |
|-------|------:|
| `Other` | 5 |
| `Marketing` | 4 |
| `Promotion` | 1 |

### `sales.salestaxrate`.`stateprovinceid` _integer_

| Value | Count |
|-------|------:|
| `1` | 2 |
| `63` | 2 |
| `57` | 2 |
| `74` | 1 |
| `36` | 1 |
| `69` | 1 |
| `31` | 1 |
| `29` | 1 |
| `30` | 1 |
| `51` | 1 |
| `41` | 1 |
| `49` | 1 |
| `14` | 1 |
| `20` | 1 |
| `83` | 1 |
| `9` | 1 |
| `7` | 1 |
| `35` | 1 |
| `45` | 1 |
| `15` | 1 |

### `sales.salestaxrate`.`taxtype` _smallint_

| Value | Count |
|-------|------:|
| `3` | 13 |
| `1` | 13 |
| `2` | 3 |

### `sales.specialoffer`.`type` _character varying_

| Value | Count |
|-------|------:|
| `Volume Discount` | 5 |
| `Excess Inventory` | 3 |
| `Seasonal Discount` | 3 |
| `Discontinued Product` | 2 |
| `New Product` | 2 |
| `No Discount` | 1 |

---
## 6. Data Profile

Only columns with `null% > 10` or numeric/date ranges are shown.

### `humanresources.department`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `departmentid` | integer | 0.0 | 16 | 1.0 | 16.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2008-04-30 00:00:00 | 2008-04-30 00:00:00 |

### `humanresources.employee`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0.0 | 290 | 1.0 | 290.0 |
| `birthdate` | date | 0.0 | 275 | 1951-10-17 | 1991-05-31 |
| `hiredate` | date | 0.0 | 164 | 2006-06-30 | 2013-05-30 |
| `vacationhours` | smallint | 0.0 | 100 | 0.0 | 99.0 |
| `sickleavehours` | smallint | 0.0 | 51 | 20.0 | 80.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 2 | 2014-06-30 00:00:00 | 2014-12-26 09:17:08.637000 |

### `humanresources.employeedepartmenthistory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0.0 | 290 | 1.0 | 290.0 |
| `departmentid` | smallint | 0.0 | 16 | 1.0 | 16.0 |
| `shiftid` | smallint | 0.0 | 3 | 1.0 | 3.0 |
| `startdate` | date | 0.0 | 170 | 2006-06-30 | 2013-11-14 |
| `enddate` | date | 98.0 | 6 | 2009-07-14 | 2013-11-13 |
| `modifieddate` | timestamp without time zone | 0.0 | 172 | 2006-06-29 00:00:00 | 2013-11-13 00:00:00 |

### `humanresources.employeepayhistory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0.0 | 290 | 1.0 | 290.0 |
| `ratechangedate` | timestamp without time zone | 0.0 | 177 | 2006-06-30 00:00:00 | 2013-07-14 00:00:00 |
| `rate` | numeric | 0.0 | 66 | 6.5 | 125.5 |
| `payfrequency` | smallint | 0.0 | 2 | 1.0 | 2.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 26 | 2007-11-21 00:00:00 | 2014-06-30 00:00:00 |

### `humanresources.jobcandidate`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `jobcandidateid` | integer | 0 | 0 | None | None |
| `businessentityid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `humanresources.shift`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `shiftid` | integer | 0.0 | 3 | 1.0 | 3.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2008-04-30 00:00:00 | 2008-04-30 00:00:00 |

### `humanresources.vemployee`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `emailpromotion` | integer | 0 | 0 | None | None |

### `humanresources.vemployeedepartment`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `startdate` | date | 0 | 0 | None | None |

### `humanresources.vemployeedepartmenthistory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `startdate` | date | 0 | 0 | None | None |
| `enddate` | date | 0 | 0 | None | None |

### `humanresources.vjobcandidate`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `jobcandidateid` | integer | 0 | 0 | None | None |
| `businessentityid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `humanresources.vjobcandidateeducation`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `jobcandidateid` | integer | 0 | 0 | None | None |
| `Edu.StartDate` | date | 0 | 0 | None | None |
| `Edu.EndDate` | date | 0 | 0 | None | None |

### `humanresources.vjobcandidateemployment`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `jobcandidateid` | integer | 0 | 0 | None | None |
| `Emp.StartDate` | date | 0 | 0 | None | None |
| `Emp.EndDate` | date | 0 | 0 | None | None |

### `person.address`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `addressid` | integer | 0.0 | 19614 | 1.0 | 32521.0 |
| `addressline2` | character varying | 98.2 | 195 |  |  |
| `stateprovinceid` | integer | 0.0 | 74 | 1.0 | 181.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1280 | 2017-06-22 00:00:00 | 2025-06-29 00:00:00 |

### `person.addresstype`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `addresstypeid` | integer | 0.0 | 6 | 1.0 | 6.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `person.businessentity`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `person.businessentityaddress`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `addressid` | integer | 0 | 0 | None | None |
| `addresstypeid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `person.businessentitycontact`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `personid` | integer | 0 | 0 | None | None |
| `contacttypeid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `person.contacttype`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `contacttypeid` | integer | 0.0 | 20 | 1.0 | 20.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `person.countryregion`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `person.emailaddress`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `emailaddressid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `person.password`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `person.person`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `emailpromotion` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `person.personphone`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `phonenumbertypeid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `person.phonenumbertype`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `phonenumbertypeid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `person.stateprovince`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `stateprovinceid` | integer | 0.0 | 181 | 1.0 | 181.0 |
| `territoryid` | integer | 0.0 | 10 | 1.0 | 10.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 2 | 2019-04-30 00:00:00 | 2025-02-07 10:17:21.587000 |

### `person.vadditionalcontactinfo`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `production.billofmaterials`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `billofmaterialsid` | integer | 0.0 | 2679 | 1.0 | 3482.0 |
| `productassemblyid` | integer | 3.8 | 238 | 3.0 | 999.0 |
| `componentid` | integer | 0.0 | 325 | 1.0 | 999.0 |
| `startdate` | timestamp without time zone | 0.0 | 19 | 2021-03-03 00:00:00 | 2021-12-22 00:00:00 |
| `enddate` | timestamp without time zone | 92.6 | 8 | 2021-05-02 00:00:00 | 2021-11-13 00:00:00 |
| `bomlevel` | smallint | 0.0 | 5 | 0.0 | 4.0 |
| `perassemblyqty` | numeric | 0.0 | 12 | 1.0 | 41.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 27 | 2021-02-17 00:00:00 | 2021-12-08 00:00:00 |

### `production.culture`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `production.document`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `owner` | integer | 0 | 0 | None | None |
| `changenumber` | integer | 0 | 0 | None | None |
| `status` | smallint | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `production.illustration`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `illustrationid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `production.location`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `locationid` | integer | 0.0 | 14 | 1.0 | 60.0 |
| `costrate` | numeric | 0.0 | 7 | 0.0 | 25.0 |
| `availability` | numeric | 0.0 | 5 | 0.0 | 120.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `production.product`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productid` | integer | 0.0 | 504 | 1.0 | 999.0 |
| `color` | character varying | 49.2 | 9 |  |  |
| `safetystocklevel` | smallint | 0.0 | 6 | 4.0 | 1000.0 |
| `reorderpoint` | smallint | 0.0 | 6 | 3.0 | 750.0 |
| `standardcost` | numeric | 0.0 | 114 | 0.0 | 2171.2942 |
| `listprice` | numeric | 0.0 | 103 | 0.0 | 3578.27 |
| `size` | character varying | 58.1 | 18 |  |  |
| `sizeunitmeasurecode` | character | 65.1 | 1 |  |  |
| `weightunitmeasurecode` | character | 59.3 | 2 |  |  |
| `weight` | numeric | 59.3 | 127 | 2.12 | 1050.0 |
| `daystomanufacture` | integer | 0.0 | 4 | 0.0 | 4.0 |
| `productline` | character | 44.8 | 4 |  |  |
| `class` | character | 51.0 | 3 |  |  |
| `style` | character | 58.1 | 3 |  |  |
| `productsubcategoryid` | integer | 41.5 | 37 | 1.0 | 37.0 |
| `productmodelid` | integer | 41.5 | 119 | 1.0 | 128.0 |
| `sellstartdate` | timestamp without time zone | 0.0 | 4 | 2019-04-30 00:00:00 | 2024-05-29 00:00:00 |
| `sellenddate` | timestamp without time zone | 80.6 | 2 | 2023-05-29 00:00:00 | 2024-05-28 00:00:00 |
| `discontinueddate` | timestamp without time zone | 100.0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0.0 | 2 | 2025-02-07 10:01:36.827000 | 2025-02-07 10:03:55.510000 |

### `production.productcategory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productcategoryid` | integer | 0.0 | 4 | 1.0 | 4.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `production.productcosthistory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productid` | integer | 0.0 | 293 | 707.0 | 999.0 |
| `startdate` | timestamp without time zone | 0.0 | 3 | 2022-05-30 00:00:00 | 2024-05-29 00:00:00 |
| `enddate` | timestamp without time zone | 49.4 | 2 | 2023-05-29 00:00:00 | 2024-05-28 00:00:00 |
| `standardcost` | numeric | 0.0 | 134 | 0.8565 | 2171.2942 |
| `modifieddate` | timestamp without time zone | 0.0 | 3 | 2023-05-29 00:00:00 | 2024-05-28 00:00:00 |

### `production.productdescription`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productdescriptionid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `production.productdocument`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productid` | integer | 0.0 | 31 | 317.0 | 999.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 2 | 2024-12-28 13:51:58.103000 | 2024-12-28 13:51:58.120000 |

### `production.productinventory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productid` | integer | 0.0 | 432 | 1.0 | 999.0 |
| `locationid` | smallint | 0.0 | 14 | 1.0 | 60.0 |
| `bin` | smallint | 0.0 | 62 | 0.0 | 61.0 |
| `quantity` | smallint | 0.0 | 343 | 0.0 | 924.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 24 | 2019-03-31 00:00:00 | 2025-08-11 00:00:00 |

### `production.productlistpricehistory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productid` | integer | 0.0 | 293 | 707.0 | 999.0 |
| `startdate` | timestamp without time zone | 0.0 | 3 | 2022-05-30 00:00:00 | 2024-05-29 00:00:00 |
| `enddate` | timestamp without time zone | 49.4 | 2 | 2023-05-29 00:00:00 | 2024-05-28 00:00:00 |
| `listprice` | numeric | 0.0 | 120 | 2.29 | 3578.27 |
| `modifieddate` | timestamp without time zone | 0.0 | 3 | 2023-05-29 00:00:00 | 2024-05-28 00:00:00 |

### `production.productmodel`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productmodelid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `production.productmodelillustration`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productmodelid` | integer | 0.0 | 5 | 7.0 | 67.0 |
| `illustrationid` | integer | 0.0 | 4 | 3.0 | 6.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 3 | 2025-01-08 14:41:02.167000 | 2025-01-08 14:41:02.200000 |

### `production.productmodelproductdescriptionculture`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productmodelid` | integer | 0.0 | 127 | 1.0 | 127.0 |
| `productdescriptionid` | integer | 0.0 | 762 | 3.0 | 2010.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2024-04-29 00:00:00 | 2024-04-29 00:00:00 |

### `production.productphoto`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productphotoid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `production.productproductphoto`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productid` | integer | 0.0 | 504 | 1.0 | 999.0 |
| `productphotoid` | integer | 0.0 | 42 | 1.0 | 179.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 4 | 2019-03-31 00:00:00 | 2024-04-29 00:00:00 |

### `production.productreview`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productreviewid` | integer | 0.0 | 4 | 1.0 | 4.0 |
| `productid` | integer | 0.0 | 3 | 709.0 | 937.0 |
| `reviewdate` | timestamp without time zone | 0.0 | 3 | 2013-09-18 00:00:00 | 2013-11-15 00:00:00 |
| `rating` | integer | 0.0 | 3 | 2.0 | 5.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 3 | 2013-09-18 00:00:00 | 2013-11-15 00:00:00 |

### `production.productsubcategory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productsubcategoryid` | integer | 0.0 | 37 | 1.0 | 37.0 |
| `productcategoryid` | integer | 0.0 | 4 | 1.0 | 4.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `production.scrapreason`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `scrapreasonid` | integer | 0.0 | 16 | 1.0 | 16.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `production.transactionhistory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `transactionid` | integer | 0.0 | 113443 | 100000.0 | 213442.0 |
| `productid` | integer | 0.0 | 441 | 1.0 | 999.0 |
| `referenceorderid` | integer | 0.0 | 37118 | 417.0 | 75123.0 |
| `referenceorderlineid` | integer | 0.0 | 72 | 0.0 | 71.0 |
| `transactiondate` | timestamp without time zone | 0.0 | 365 | 2024-07-30 00:00:00 | 2025-08-02 00:00:00 |
| `quantity` | integer | 0.0 | 455 | 1.0 | 39270.0 |
| `actualcost` | numeric | 0.0 | 252 | 0.0 | 2443.35 |
| `modifieddate` | timestamp without time zone | 0.0 | 365 | 2024-07-30 00:00:00 | 2025-08-02 00:00:00 |

### `production.transactionhistoryarchive`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `transactionid` | integer | 0.0 | 89253 | 1.0 | 89253.0 |
| `productid` | integer | 0.0 | 497 | 1.0 | 999.0 |
| `referenceorderid` | integer | 0.0 | 51380 | 1.0 | 53449.0 |
| `referenceorderlineid` | integer | 0.0 | 73 | 0.0 | 72.0 |
| `transactiondate` | timestamp without time zone | 0.0 | 794 | 2022-04-15 00:00:00 | 2024-07-29 00:00:00 |
| `quantity` | integer | 0.0 | 640 | 1.0 | 39570.0 |
| `actualcost` | numeric | 0.0 | 293 | 0.0 | 3578.27 |
| `modifieddate` | timestamp without time zone | 0.0 | 794 | 2022-04-15 00:00:00 | 2024-07-29 00:00:00 |

### `production.unitmeasure`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `production.vproductmodelcatalogdescription`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productmodelid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `production.vproductmodelinstructions`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productmodelid` | integer | 0 | 0 | None | None |
| `LocationID` | integer | 0 | 0 | None | None |
| `SetupHours` | numeric | 0 | 0 | None | None |
| `MachineHours` | numeric | 0 | 0 | None | None |
| `LaborHours` | numeric | 0 | 0 | None | None |
| `LotSize` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `production.workorder`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `workorderid` | integer | 0.0 | 72591 | 1.0 | 72591.0 |
| `productid` | integer | 0.0 | 238 | 3.0 | 999.0 |
| `orderqty` | integer | 0.0 | 903 | 1.0 | 39570.0 |
| `scrappedqty` | smallint | 0.0 | 87 | 0.0 | 673.0 |
| `startdate` | timestamp without time zone | 0.0 | 1093 | 2022-06-02 00:00:00 | 2025-06-01 00:00:00 |
| `enddate` | timestamp without time zone | 0.0 | 1098 | 2022-06-12 00:00:00 | 2025-06-16 00:00:00 |
| `duedate` | timestamp without time zone | 0.0 | 1093 | 2022-06-13 00:00:00 | 2025-06-12 00:00:00 |
| `scrapreasonid` | smallint | 99.0 | 16 | 1.0 | 16.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1098 | 2022-06-12 00:00:00 | 2025-06-16 00:00:00 |

### `production.workorderrouting`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `workorderid` | integer | 0.0 | 42625 | 13.0 | 72587.0 |
| `productid` | integer | 0.0 | 149 | 514.0 | 999.0 |
| `operationsequence` | smallint | 0.0 | 7 | 1.0 | 7.0 |
| `locationid` | smallint | 0.0 | 7 | 10.0 | 60.0 |
| `scheduledstartdate` | timestamp without time zone | 0.0 | 1093 | 2022-06-02 00:00:00 | 2025-06-01 00:00:00 |
| `scheduledenddate` | timestamp without time zone | 0.0 | 1093 | 2022-06-13 00:00:00 | 2025-06-12 00:00:00 |
| `actualstartdate` | timestamp without time zone | 0.0 | 671 | 2022-06-02 00:00:00 | 2025-06-16 00:00:00 |
| `actualenddate` | timestamp without time zone | 0.0 | 714 | 2022-06-14 00:00:00 | 2025-06-27 00:00:00 |
| `actualresourcehrs` | numeric | 0.0 | 6 | 1.0 | 4.1 |
| `plannedcost` | numeric | 0.0 | 7 | 14.5 | 92.25 |
| `actualcost` | numeric | 0.0 | 7 | 14.5 | 92.25 |
| `modifieddate` | timestamp without time zone | 0.0 | 714 | 2022-06-14 00:00:00 | 2025-06-27 00:00:00 |

### `purchasing.productvendor`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `productid` | integer | 0.0 | 265 | 1.0 | 952.0 |
| `businessentityid` | integer | 0.0 | 86 | 1492.0 | 1698.0 |
| `averageleadtime` | integer | 0.0 | 13 | 10.0 | 120.0 |
| `standardprice` | numeric | 0.0 | 175 | 0.2 | 78.89 |
| `lastreceiptcost` | numeric | 0.0 | 175 | 0.21 | 82.8345 |
| `lastreceiptdate` | timestamp without time zone | 0.0 | 43 | 2022-07-21 00:00:00 | 2025-10-21 00:00:00 |
| `minorderqty` | integer | 0.0 | 11 | 1.0 | 5000.0 |
| `maxorderqty` | integer | 0.0 | 16 | 5.0 | 15000.0 |
| `onorderqty` | integer | 66.3 | 26 | 3.0 | 8000.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 31 | 2022-07-21 00:00:00 | 2026-08-11 12:20:28.343000 |

### `purchasing.purchaseorderdetail`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `purchaseorderid` | integer | 0.0 | 4012 | 1.0 | 4012.0 |
| `purchaseorderdetailid` | integer | 0.0 | 8845 | 1.0 | 8845.0 |
| `duedate` | timestamp without time zone | 0.0 | 299 | 2022-04-29 00:00:00 | 2025-10-21 00:00:00 |
| `orderqty` | smallint | 0.0 | 28 | 3.0 | 8000.0 |
| `productid` | integer | 0.0 | 265 | 1.0 | 952.0 |
| `unitprice` | numeric | 0.0 | 177 | 0.21 | 82.8345 |
| `receivedqty` | numeric | 0.0 | 34 | 2.0 | 8000.0 |
| `rejectedqty` | numeric | 0.0 | 13 | 0.0 | 1250.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 308 | 2022-04-22 00:00:00 | 2026-08-11 12:25:46.483000 |

### `purchasing.purchaseorderheader`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `purchaseorderid` | integer | 0.0 | 4012 | 1.0 | 4012.0 |
| `revisionnumber` | smallint | 0.0 | 10 | 5.0 | 21.0 |
| `status` | smallint | 0.0 | 4 | 1.0 | 4.0 |
| `employeeid` | integer | 0.0 | 12 | 250.0 | 261.0 |
| `vendorid` | integer | 0.0 | 86 | 1492.0 | 1698.0 |
| `shipmethodid` | integer | 0.0 | 5 | 1.0 | 5.0 |
| `orderdate` | timestamp without time zone | 0.0 | 300 | 2022-04-15 00:00:00 | 2025-09-21 00:00:00 |
| `shipdate` | timestamp without time zone | 0.0 | 297 | 2022-04-24 00:00:00 | 2025-10-16 00:00:00 |
| `subtotal` | numeric | 0.0 | 351 | 37.0755 | 997680.0 |
| `taxamt` | numeric | 0.0 | 351 | 2.966 | 79814.4 |
| `freight` | numeric | 0.0 | 351 | 0.9269 | 19953.6 |
| `modifieddate` | timestamp without time zone | 0.0 | 306 | 2022-04-24 00:00:00 | 2026-08-11 12:25:46.483000 |

### `purchasing.shipmethod`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `shipmethodid` | integer | 0.0 | 5 | 1.0 | 5.0 |
| `shipbase` | numeric | 0.0 | 5 | 3.95 | 29.95 |
| `shiprate` | numeric | 0.0 | 5 | 0.99 | 2.99 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `purchasing.vendor`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0.0 | 104 | 1492.0 | 1698.0 |
| `creditrating` | smallint | 0.0 | 5 | 1.0 | 5.0 |
| `purchasingwebserviceurl` | character varying | 94.2 | 6 |  |  |
| `modifieddate` | timestamp without time zone | 0.0 | 10 | 2022-04-24 00:00:00 | 2023-02-17 00:00:00 |

### `purchasing.vvendorwithaddresses`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |

### `purchasing.vvendorwithcontacts`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `emailpromotion` | integer | 0 | 0 | None | None |

### `sales.countryregioncurrency`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `modifieddate` | timestamp without time zone | 0.0 | 2 | 2019-04-30 00:00:00 | 2025-02-07 10:17:21.510000 |

### `sales.creditcard`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `creditcardid` | integer | 0.0 | 19118 | 1.0 | 19237.0 |
| `expmonth` | smallint | 0.0 | 12 | 1.0 | 12.0 |
| `expyear` | smallint | 0.0 | 4 | 2005.0 | 2008.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1279 | 2017-06-22 00:00:00 | 2025-06-29 00:00:00 |

### `sales.currency`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `sales.currencyrate`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `currencyrateid` | integer | 0.0 | 13532 | 1.0 | 13532.0 |
| `currencyratedate` | timestamp without time zone | 0.0 | 1097 | 2022-05-30 00:00:00 | 2025-05-30 00:00:00 |
| `averagerate` | numeric | 0.0 | 6127 | 0.6046 | 1500.0 |
| `endofdayrate` | numeric | 0.0 | 7232 | 0.6041 | 1499.95 |
| `modifieddate` | timestamp without time zone | 0.0 | 1098 | 2022-05-30 00:00:00 | 2025-05-30 00:00:00 |

### `sales.customer`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `customerid` | integer | 0.0 | 19820 | 1.0 | 30118.0 |
| `personid` | integer | 3.5 | 19119 | 291.0 | 20777.0 |
| `storeid` | integer | 93.3 | 701 | 292.0 | 2051.0 |
| `territoryid` | integer | 0.0 | 10 | 1.0 | 10.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2025-09-11 11:15:07.263000 | 2025-09-11 11:15:07.263000 |

### `sales.personcreditcard`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0.0 | 19118 | 293.0 | 20777.0 |
| `creditcardid` | integer | 0.0 | 19118 | 1.0 | 19237.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1124 | 2022-05-30 00:00:00 | 2025-06-29 00:00:00 |

### `sales.salesorderdetail`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `salesorderid` | integer | 0.0 | 31465 | 43659.0 | 75123.0 |
| `salesorderdetailid` | integer | 0.0 | 121317 | 1.0 | 121317.0 |
| `carriertrackingnumber` | character varying | 49.8 | 3806 |  |  |
| `orderqty` | smallint | 0.0 | 41 | 1.0 | 44.0 |
| `productid` | integer | 0.0 | 266 | 707.0 | 999.0 |
| `specialofferid` | integer | 0.0 | 12 | 1.0 | 16.0 |
| `unitprice` | numeric | 0.0 | 287 | 1.3282 | 3578.27 |
| `unitpricediscount` | numeric | 0.0 | 9 | 0.0 | 0.4 |
| `modifieddate` | timestamp without time zone | 0.0 | 1124 | 2022-05-30 00:00:00 | 2025-06-29 00:00:00 |

### `sales.salesorderheader`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `salesorderid` | integer | 0.0 | 31465 | 43659.0 | 75123.0 |
| `revisionnumber` | smallint | 0.0 | 2 | 10.0 | 11.0 |
| `orderdate` | timestamp without time zone | 0.0 | 1124 | 2022-05-30 00:00:00 | 2025-06-29 00:00:00 |
| `duedate` | timestamp without time zone | 0.0 | 1124 | 2022-06-11 00:00:00 | 2025-07-11 00:00:00 |
| `shipdate` | timestamp without time zone | 0.0 | 1124 | 2022-06-06 00:00:00 | 2025-07-06 00:00:00 |
| `status` | smallint | 0.0 | 1 | 5.0 | 5.0 |
| `purchaseordernumber` | character varying | 87.9 | 3806 |  |  |
| `customerid` | integer | 0.0 | 19119 | 11000.0 | 30118.0 |
| `salespersonid` | integer | 87.9 | 17 | 274.0 | 290.0 |
| `territoryid` | integer | 0.0 | 10 | 1.0 | 10.0 |
| `billtoaddressid` | integer | 0.0 | 19119 | 405.0 | 29883.0 |
| `shiptoaddressid` | integer | 0.0 | 19119 | 9.0 | 29883.0 |
| `shipmethodid` | integer | 0.0 | 2 | 1.0 | 5.0 |
| `creditcardid` | integer | 3.6 | 18384 | 1.0 | 19237.0 |
| `currencyrateid` | integer | 55.6 | 2514 | 2.0 | 12431.0 |
| `subtotal` | numeric | 0.0 | 4747 | 1.374 | 163930.3943 |
| `taxamt` | numeric | 0.0 | 4745 | 0.1099 | 17948.5186 |
| `freight` | numeric | 0.0 | 4744 | 0.0344 | 5608.9121 |
| `totaldue` | numeric | 0.0 | 4754 | 1.5183 | 187487.825 |
| `comment` | character varying | 100.0 | 0 |  |  |
| `modifieddate` | timestamp without time zone | 0.0 | 1124 | 2022-06-06 00:00:00 | 2025-07-06 00:00:00 |

### `sales.salesorderheadersalesreason`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `salesorderid` | integer | 0.0 | 23012 | 43697.0 | 75123.0 |
| `salesreasonid` | integer | 0.0 | 7 | 1.0 | 10.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1109 | 2022-05-30 00:00:00 | 2025-06-29 00:00:00 |

### `sales.salesperson`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0.0 | 17 | 274.0 | 290.0 |
| `territoryid` | integer | 17.6 | 10 | 1.0 | 10.0 |
| `salesquota` | numeric | 17.6 | 2 | 250000.0 | 300000.0 |
| `bonus` | numeric | 0.0 | 14 | 0.0 | 6700.0 |
| `commissionpct` | numeric | 0.0 | 8 | 0.0 | 0.02 |
| `salesytd` | numeric | 0.0 | 17 | 172524.4512 | 4251368.5497 |
| `saleslastyear` | numeric | 0.0 | 14 | 0.0 | 2396539.7601 |
| `modifieddate` | timestamp without time zone | 0.0 | 7 | 2021-12-27 00:00:00 | 2024-05-22 00:00:00 |

### `sales.salespersonquotahistory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0.0 | 17 | 274.0 | 290.0 |
| `quotadate` | timestamp without time zone | 0.0 | 12 | 2022-05-30 00:00:00 | 2025-02-28 00:00:00 |
| `salesquota` | numeric | 0.0 | 154 | 1000.0 | 1898000.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 12 | 2022-04-15 00:00:00 | 2025-01-14 00:00:00 |

### `sales.salesreason`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `salesreasonid` | integer | 0.0 | 10 | 1.0 | 10.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `sales.salestaxrate`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `salestaxrateid` | integer | 0.0 | 29 | 1.0 | 31.0 |
| `stateprovinceid` | integer | 0.0 | 26 | 1.0 | 84.0 |
| `taxtype` | smallint | 0.0 | 3 | 1.0 | 3.0 |
| `taxrate` | numeric | 0.0 | 15 | 5.0 | 19.6 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `sales.salesterritory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `territoryid` | integer | 0.0 | 10 | 1.0 | 10.0 |
| `salesytd` | numeric | 0.0 | 10 | 2402176.8476 | 10510853.8739 |
| `saleslastyear` | numeric | 0.0 | 10 | 1307949.7917 | 5693988.86 |
| `costytd` | numeric | 0.0 | 1 | 0.0 | 0.0 |
| `costlastyear` | numeric | 0.0 | 1 | 0.0 | 0.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2019-04-30 00:00:00 | 2019-04-30 00:00:00 |

### `sales.salesterritoryhistory`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0.0 | 14 | 275.0 | 290.0 |
| `territoryid` | integer | 0.0 | 10 | 1.0 | 10.0 |
| `startdate` | timestamp without time zone | 0.0 | 5 | 2022-05-30 00:00:00 | 2024-05-29 00:00:00 |
| `enddate` | timestamp without time zone | 76.5 | 3 | 2023-05-29 00:00:00 | 2023-11-29 00:00:00 |
| `modifieddate` | timestamp without time zone | 0.0 | 8 | 2022-05-23 00:00:00 | 2024-05-22 00:00:00 |

### `sales.shoppingcartitem`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `shoppingcartitemid` | integer | 0.0 | 3 | 2.0 | 5.0 |
| `quantity` | integer | 0.0 | 3 | 3.0 | 7.0 |
| `productid` | integer | 0.0 | 3 | 862.0 | 881.0 |
| `datecreated` | timestamp without time zone | 0.0 | 1 | 2024-11-08 17:54:07.603000 | 2024-11-08 17:54:07.603000 |
| `modifieddate` | timestamp without time zone | 0.0 | 1 | 2024-11-08 17:54:07.603000 | 2024-11-08 17:54:07.603000 |

### `sales.specialoffer`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `specialofferid` | integer | 0.0 | 16 | 1.0 | 16.0 |
| `discountpct` | numeric | 0.0 | 10 | 0.0 | 0.5 |
| `startdate` | timestamp without time zone | 0.0 | 8 | 2022-04-30 00:00:00 | 2025-03-30 00:00:00 |
| `enddate` | timestamp without time zone | 0.0 | 10 | 2023-05-29 00:00:00 | 2025-11-29 00:00:00 |
| `minqty` | integer | 0.0 | 6 | 0.0 | 61.0 |
| `maxqty` | integer | 75.0 | 4 | 14.0 | 60.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 8 | 2022-03-31 00:00:00 | 2025-02-28 00:00:00 |

### `sales.specialofferproduct`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `specialofferid` | integer | 0.0 | 15 | 1.0 | 16.0 |
| `productid` | integer | 0.0 | 295 | 680.0 | 999.0 |
| `modifieddate` | timestamp without time zone | 0.0 | 8 | 2022-03-31 00:00:00 | 2025-02-28 00:00:00 |

### `sales.store`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `salespersonid` | integer | 0 | 0 | None | None |
| `modifieddate` | timestamp without time zone | 0 | 0 | None | None |

### `sales.vindividualcustomer`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `emailpromotion` | integer | 0 | 0 | None | None |

### `sales.vpersondemographics`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `datefirstpurchase` | date | 0 | 0 | None | None |
| `birthdate` | date | 0 | 0 | None | None |
| `totalchildren` | integer | 0 | 0 | None | None |
| `numberchildrenathome` | integer | 0 | 0 | None | None |
| `numbercarsowned` | integer | 0 | 0 | None | None |

### `sales.vsalesperson`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `emailpromotion` | integer | 0 | 0 | None | None |
| `salesquota` | numeric | 0 | 0 | None | None |
| `salesytd` | numeric | 0 | 0 | None | None |
| `saleslastyear` | numeric | 0 | 0 | None | None |

### `sales.vsalespersonsalesbyfiscalyears`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `SalesPersonID` | integer | 0 | 0 | None | None |
| `2012` | numeric | 0 | 0 | None | None |
| `2013` | numeric | 0 | 0 | None | None |
| `2014` | numeric | 0 | 0 | None | None |

### `sales.vsalespersonsalesbyfiscalyearsdata`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `salespersonid` | integer | 0 | 0 | None | None |
| `salestotal` | numeric | 0 | 0 | None | None |
| `fiscalyear` | numeric | 0 | 0 | None | None |

### `sales.vstorewithaddresses`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |

### `sales.vstorewithcontacts`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `emailpromotion` | integer | 0 | 0 | None | None |

### `sales.vstorewithdemographics`

| Column | Type | Null% | Distinct | Min | Max |
|--------|------|------:|---------:|-----|-----|
| `businessentityid` | integer | 0 | 0 | None | None |
| `YearOpened` | integer | 0 | 0 | None | None |
| `SquareFeet` | integer | 0 | 0 | None | None |
| `NumberEmployees` | integer | 0 | 0 | None | None |

---
## 7. Lifecycle Trace

Traces one order from **Sales → Production → Purchasing**.

### Pipeline aggregate (all orders)

| Metric | Value |
|--------|-------|
| Total orders | 31,465 |
| Shipped (status=5) | 31,465 |
| Rejected (status=4) | 0 |
| In-process (status=1) | 0 |
| Avg days to ship | 7.0 |
| Avg days to due | 12.0 |
| Order date range | 2022-05-30 00:00:00 → 2025-06-29 00:00:00 |

### Sample order: #51131  _(highest value shipped)_

| Field | Value |
|-------|-------|
| Customer | None |
| Sales rep | None |
| Territory | Southwest |
| Order date | 2024-05-29 00:00:00 |
| Ship date | 2024-06-05 00:00:00 |
| Total due | $187,487.83 |

### Work orders triggered (Production domain)

| WO# | Product | Qty | Start | End |
|-----|---------|----:|-------|-----|
| 36569 | LL Touring Frame - Yellow, 62 | 38 | 2024-06-01 | 2024-06-11 |
| 36570 | HL Touring Frame - Yellow, 46 | 14 | 2024-06-01 | 2024-06-11 |
| 36571 | HL Touring Frame - Yellow, 50 | 16 | 2024-06-01 | 2024-06-11 |
| 36572 | HL Touring Frame - Yellow, 54 | 24 | 2024-06-01 | 2024-06-11 |
| 36573 | HL Touring Frame - Blue, 46 | 12 | 2024-06-01 | 2024-06-11 |
| 36574 | HL Touring Frame - Blue, 50 | 18 | 2024-06-01 | 2024-06-11 |
| 36575 | HL Touring Frame - Blue, 54 | 57 | 2024-06-01 | 2024-06-11 |
| 36576 | HL Touring Frame - Blue, 60 | 43 | 2024-06-01 | 2024-06-11 |
| 36578 | LL Touring Frame - Blue, 50 | 24 | 2024-06-01 | 2024-06-11 |
| 36568 | HL Touring Frame - Yellow, 60 | 29 | 2024-06-01 | 2024-06-11 |

### Purchase orders for same products (Purchasing domain)

| PO# | Vendor | Product | Ordered | Received |
|-----|--------|---------|--------:|---------:|
| 12 | Bicycle Specialists | Touring Pedal | 550 | 550.00 |
| 91 | Bicycle Specialists | Touring Pedal | 550 | 550.00 |
| 98 | Chicago City Saddles | LL Touring Seat/Saddle | 550 | 550.00 |
| 98 | Chicago City Saddles | ML Touring Seat/Saddle | 550 | 550.00 |
| 98 | Chicago City Saddles | HL Touring Seat/Saddle | 550 | 550.00 |
| 170 | Bicycle Specialists | Touring Pedal | 550 | 550.00 |
| 191 | Expert Bike Co | LL Touring Seat/Saddle | 550 | 550.00 |
| 191 | Expert Bike Co | ML Touring Seat/Saddle | 550 | 550.00 |
| 256 | Chicago City Saddles | LL Touring Seat/Saddle | 550 | 468.00 |
| 249 | Bicycle Specialists | Touring Pedal | 550 | 550.00 |
