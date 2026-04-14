# Foreign Key Graph — Complete Reference

**Total FK edges: 65. Cross-schema: 0. All constraints are intra-schema.**

Cross-domain relationships (sales ↔ production ↔ purchasing) are enforced by convention on `productid` and `businessentityid`. No FK enforces them.

---

## humanresources

```
humanresources.employeedepartmenthistory.businessentityid → humanresources.employee.businessentityid
humanresources.employeedepartmenthistory.departmentid     → humanresources.department.departmentid
humanresources.employeedepartmenthistory.shiftid          → humanresources.shift.shiftid
humanresources.employeepayhistory.businessentityid        → humanresources.employee.businessentityid
humanresources.jobcandidate.businessentityid              → humanresources.employee.businessentityid
```

---

## person

```
person.address.stateprovinceid                   → person.stateprovince.stateprovinceid
person.businessentityaddress.addressid           → person.address.addressid
person.businessentityaddress.addresstypeid       → person.addresstype.addresstypeid
person.businessentityaddress.businessentityid    → person.businessentity.businessentityid
person.businessentitycontact.businessentityid    → person.businessentity.businessentityid
person.businessentitycontact.contacttypeid       → person.contacttype.contacttypeid
person.businessentitycontact.personid            → person.person.businessentityid
person.emailaddress.businessentityid             → person.person.businessentityid
person.password.businessentityid                 → person.person.businessentityid
person.person.businessentityid                   → person.businessentity.businessentityid
person.personphone.businessentityid              → person.person.businessentityid
person.personphone.phonenumbertypeid             → person.phonenumbertype.phonenumbertypeid
person.stateprovince.countryregioncode           → person.countryregion.countryregioncode
```

---

## production

```
production.billofmaterials.componentid                    → production.product.productid
production.billofmaterials.productassemblyid              → production.product.productid
production.billofmaterials.unitmeasurecode                → production.unitmeasure.unitmeasurecode
production.product.productsubcategoryid                   → production.productsubcategory.productsubcategoryid
production.product.sizeunitmeasurecode                    → production.unitmeasure.unitmeasurecode
production.product.weightunitmeasurecode                  → production.unitmeasure.unitmeasurecode
production.productcosthistory.productid                   → production.product.productid
production.productdocument.productid                      → production.product.productid
production.productinventory.locationid                    → production.location.locationid
production.productinventory.productid                     → production.product.productid
production.productlistpricehistory.productid              → production.product.productid
production.productmodelproductdescriptionculture.cultureid → production.culture.cultureid
production.productproductphoto.productid                  → production.product.productid
production.productreview.productid                        → production.product.productid
production.productsubcategory.productcategoryid           → production.productcategory.productcategoryid
production.transactionhistory.productid                   → production.product.productid
production.workorder.productid                            → production.product.productid
production.workorder.scrapreasonid                        → production.scrapreason.scrapreasonid
production.workorderrouting.locationid                    → production.location.locationid
production.workorderrouting.workorderid                   → production.workorder.workorderid
```

---

## purchasing

```
purchasing.productvendor.businessentityid         → purchasing.vendor.businessentityid
purchasing.purchaseorderdetail.purchaseorderid    → purchasing.purchaseorderheader.purchaseorderid
purchasing.purchaseorderheader.shipmethodid       → purchasing.shipmethod.shipmethodid
purchasing.purchaseorderheader.vendorid           → purchasing.vendor.businessentityid
```

---

## sales

```
sales.countryregioncurrency.currencycode          → sales.currency.currencycode
sales.currencyrate.fromcurrencycode               → sales.currency.currencycode
sales.currencyrate.tocurrencycode                 → sales.currency.currencycode
sales.customer.territoryid                        → sales.salesterritory.territoryid
sales.personcreditcard.creditcardid               → sales.creditcard.creditcardid
sales.salesorderdetail.productid                  → sales.specialofferproduct.productid
sales.salesorderdetail.productid                  → sales.specialofferproduct.specialofferid
sales.salesorderdetail.salesorderid               → sales.salesorderheader.salesorderid
sales.salesorderdetail.specialofferid             → sales.specialofferproduct.productid
sales.salesorderdetail.specialofferid             → sales.specialofferproduct.specialofferid
sales.salesorderheader.creditcardid               → sales.creditcard.creditcardid
sales.salesorderheader.currencyrateid             → sales.currencyrate.currencyrateid
sales.salesorderheader.customerid                 → sales.customer.customerid
sales.salesorderheader.salespersonid              → sales.salesperson.businessentityid
sales.salesorderheader.territoryid                → sales.salesterritory.territoryid
sales.salesorderheadersalesreason.salesorderid    → sales.salesorderheader.salesorderid
sales.salesorderheadersalesreason.salesreasonid   → sales.salesreason.salesreasonid
sales.salesperson.territoryid                     → sales.salesterritory.territoryid
sales.salespersonquotahistory.businessentityid    → sales.salesperson.businessentityid
sales.salesterritoryhistory.businessentityid      → sales.salesperson.businessentityid
sales.salesterritoryhistory.territoryid           → sales.salesterritory.territoryid
sales.specialofferproduct.specialofferid          → sales.specialoffer.specialofferid
sales.store.salespersonid                         → sales.salesperson.businessentityid
```

---

## Cross-domain joins (convention, no FK enforcement)

| Join | Purpose |
|---|---|
| `salesorderdetail.productid = workorder.productid` | Link sold products to manufacturing work orders |
| `salesorderdetail.productid = transactionhistory.productid WHERE transactiontype='S'` | Link orders to event log |
| `workorder.productid = transactionhistory.productid WHERE transactiontype='W'` | Link work orders to event log |
| `purchaseorderdetail.productid = transactionhistory.productid WHERE transactiontype='P'` | Link POs to event log |
| `purchaseorderdetail.productid = workorder.productid` | Link purchased components to work orders |
| `salesperson.businessentityid = employee.businessentityid` | Identify which employees are sales reps |
| `purchaseorderheader.employeeid = employee.businessentityid` | Identify which employees place POs |
| `vendor.businessentityid = person.person.businessentityid` | Resolve vendor as a person (person schema is empty) |
