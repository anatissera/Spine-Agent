"""Operational Spine — reconstruct a unified SalesOrder from AdventureWorks.

The spine is the root operational object of the business.  Given an order ID it
joins across Sales, Production, Person, and Purchasing domains to produce a
single ``SpineOrder`` Pydantic model.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from agent.db import get_connection

# ── Status codes from AdventureWorks ─────────────────────────────────────────

ORDER_STATUS = {
    1: "In Process",
    2: "Approved",
    3: "Backordered",
    4: "Rejected",
    5: "Shipped",
    6: "Cancelled",
}

# ── Pydantic models ──────────────────────────────────────────────────────────


class AddressInfo(BaseModel):
    address_line1: str
    address_line2: str | None = None
    city: str
    postal_code: str
    state_province: str | None = None


class CustomerInfo(BaseModel):
    customer_id: int
    person_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    store_id: int | None = None
    store_name: str | None = None


class SalesPersonInfo(BaseModel):
    business_entity_id: int
    first_name: str
    last_name: str
    sales_quota: Decimal | None = None
    commission_pct: Decimal


class OrderLineItem(BaseModel):
    line_number: int
    product_id: int
    product_name: str
    product_number: str
    color: str | None = None
    order_qty: int
    unit_price: Decimal
    unit_price_discount: Decimal
    line_total: Decimal
    carrier_tracking_number: str | None = None
    standard_cost: Decimal
    list_price: Decimal


class ProductInventory(BaseModel):
    product_id: int
    product_name: str
    total_quantity: int
    locations: list[dict]


class SpineOrder(BaseModel):
    """Unified representation of a SalesOrder across all domains."""

    # Identity
    spine_object_id: str  # "SalesOrder:{id}"
    sales_order_id: int

    # Header
    status: int
    status_label: str
    order_date: datetime
    due_date: datetime
    ship_date: datetime | None = None
    online_order: bool
    purchase_order_number: str | None = None
    account_number: str | None = None

    # Financials
    subtotal: Decimal
    tax: Decimal
    freight: Decimal
    total_due: Decimal

    # Relationships
    customer: CustomerInfo
    sales_person: SalesPersonInfo | None = None
    ship_to: AddressInfo
    bill_to: AddressInfo
    ship_method: str | None = None

    # Line items & inventory
    items: list[OrderLineItem]
    inventory: list[ProductInventory]


# ── SQL ──────────────────────────────────────────────────────────────────────

_HEADER_SQL = """\
SELECT
    soh.salesorderid, soh.status, soh.orderdate, soh.duedate, soh.shipdate,
    soh.subtotal, soh.taxamt, soh.freight, soh.totaldue,
    soh.onlineorderflag, soh.purchaseordernumber, soh.accountnumber,
    c.customerid, c.personid, c.storeid,
    p.firstname, p.lastname,
    ea.emailaddress,
    pp.phonenumber,
    s.name       AS store_name,
    sm.name      AS ship_method_name,
    -- shipping address
    ship_a.addressline1  AS ship_addr1,
    ship_a.addressline2  AS ship_addr2,
    ship_a.city          AS ship_city,
    ship_a.postalcode    AS ship_zip,
    ship_sp.name         AS ship_state,
    -- billing address
    bill_a.addressline1  AS bill_addr1,
    bill_a.addressline2  AS bill_addr2,
    bill_a.city          AS bill_city,
    bill_a.postalcode    AS bill_zip,
    bill_sp.name         AS bill_state,
    -- salesperson
    sp_p.firstname   AS sp_firstname,
    sp_p.lastname    AS sp_lastname,
    sp.salesquota,
    sp.commissionpct
FROM sales.salesorderheader soh
JOIN  sales.customer         c       ON c.customerid        = soh.customerid
LEFT JOIN person.person      p       ON p.businessentityid  = c.personid
LEFT JOIN person.emailaddress ea     ON ea.businessentityid = c.personid
LEFT JOIN person.personphone pp      ON pp.businessentityid = c.personid
LEFT JOIN sales.store        s       ON s.businessentityid  = c.storeid
LEFT JOIN purchasing.shipmethod sm   ON sm.shipmethodid     = soh.shipmethodid
LEFT JOIN person.address     ship_a  ON ship_a.addressid    = soh.shiptoaddressid
LEFT JOIN person.stateprovince ship_sp ON ship_sp.stateprovinceid = ship_a.stateprovinceid
LEFT JOIN person.address     bill_a  ON bill_a.addressid    = soh.billtoaddressid
LEFT JOIN person.stateprovince bill_sp ON bill_sp.stateprovinceid = bill_a.stateprovinceid
LEFT JOIN sales.salesperson  sp      ON sp.businessentityid = soh.salespersonid
LEFT JOIN person.person      sp_p    ON sp_p.businessentityid = soh.salespersonid
WHERE soh.salesorderid = %(order_id)s
LIMIT 1
"""

_ITEMS_SQL = """\
SELECT
    sod.salesorderdetailid,
    sod.orderqty,
    sod.unitprice,
    sod.unitpricediscount,
    sod.carriertrackingnumber,
    prod.productid,
    prod.name,
    prod.productnumber,
    prod.color,
    prod.standardcost,
    prod.listprice
FROM sales.salesorderdetail sod
JOIN production.product prod ON prod.productid = sod.productid
WHERE sod.salesorderid = %(order_id)s
ORDER BY sod.salesorderdetailid
"""

_INVENTORY_SQL = """\
SELECT
    pi.productid,
    prod.name,
    pi.quantity,
    pi.shelf,
    pi.bin,
    loc.name AS location_name
FROM production.productinventory pi
JOIN production.product  prod ON prod.productid  = pi.productid
JOIN production.location loc  ON loc.locationid  = pi.locationid
WHERE pi.productid IN (
    SELECT DISTINCT productid
    FROM sales.salesorderdetail
    WHERE salesorderid = %(order_id)s
)
ORDER BY pi.productid, loc.name
"""

# ── Public API ───────────────────────────────────────────────────────────────


async def get_spine(order_id: int) -> SpineOrder | None:
    """Reconstruct the unified spine object for *order_id*.

    Executes three queries (header, items, inventory) and assembles a
    :class:`SpineOrder`.  Returns ``None`` if the order does not exist.
    """
    async with await get_connection() as conn:
        # 1. Header + customer + addresses + salesperson
        row = await (await conn.execute(_HEADER_SQL, {"order_id": order_id})).fetchone()
        if row is None:
            return None

        # 2. Line items
        item_rows = await (await conn.execute(_ITEMS_SQL, {"order_id": order_id})).fetchall()

        # 3. Inventory for products in the order
        inv_rows = await (await conn.execute(_INVENTORY_SQL, {"order_id": order_id})).fetchall()

    return _assemble(row, item_rows, inv_rows, order_id)


def _assemble(
    h: dict,
    item_rows: list[dict],
    inv_rows: list[dict],
    order_id: int,
) -> SpineOrder:
    """Build a SpineOrder from raw query results."""

    customer = CustomerInfo(
        customer_id=h["customerid"],
        person_id=h["personid"],
        first_name=h["firstname"],
        last_name=h["lastname"],
        email=h["emailaddress"],
        phone=h["phonenumber"],
        store_id=h["storeid"],
        store_name=h["store_name"],
    )

    sales_person = None
    if h["sp_firstname"] is not None:
        sales_person = SalesPersonInfo(
            business_entity_id=h["salesorderid"],  # placeholder
            first_name=h["sp_firstname"],
            last_name=h["sp_lastname"],
            sales_quota=h["salesquota"],
            commission_pct=h["commissionpct"],
        )

    ship_to = AddressInfo(
        address_line1=h["ship_addr1"] or "",
        address_line2=h["ship_addr2"],
        city=h["ship_city"] or "",
        postal_code=h["ship_zip"] or "",
        state_province=h["ship_state"],
    )
    bill_to = AddressInfo(
        address_line1=h["bill_addr1"] or "",
        address_line2=h["bill_addr2"],
        city=h["bill_city"] or "",
        postal_code=h["bill_zip"] or "",
        state_province=h["bill_state"],
    )

    items = [
        OrderLineItem(
            line_number=r["salesorderdetailid"],
            product_id=r["productid"],
            product_name=r["name"],
            product_number=r["productnumber"],
            color=r["color"],
            order_qty=r["orderqty"],
            unit_price=r["unitprice"],
            unit_price_discount=r["unitpricediscount"],
            line_total=Decimal(r["orderqty"]) * r["unitprice"] * (1 - r["unitpricediscount"]),
            carrier_tracking_number=r["carriertrackingnumber"],
            standard_cost=r["standardcost"],
            list_price=r["listprice"],
        )
        for r in item_rows
    ]

    # Group inventory rows by product
    inv_by_product: dict[int, list[dict]] = defaultdict(list)
    product_names: dict[int, str] = {}
    for r in inv_rows:
        pid = r["productid"]
        product_names[pid] = r["name"]
        inv_by_product[pid].append({
            "location_name": r["location_name"],
            "quantity": r["quantity"],
            "shelf": r["shelf"],
            "bin": r["bin"],
        })

    inventory = [
        ProductInventory(
            product_id=pid,
            product_name=product_names[pid],
            total_quantity=sum(loc["quantity"] for loc in locs),
            locations=locs,
        )
        for pid, locs in inv_by_product.items()
    ]

    status = int(h["status"])
    return SpineOrder(
        spine_object_id=f"SalesOrder:{order_id}",
        sales_order_id=order_id,
        status=status,
        status_label=ORDER_STATUS.get(status, f"Unknown ({status})"),
        order_date=h["orderdate"],
        due_date=h["duedate"],
        ship_date=h["shipdate"],
        online_order=bool(h["onlineorderflag"]),
        purchase_order_number=h["purchaseordernumber"],
        account_number=h["accountnumber"],
        subtotal=h["subtotal"],
        tax=h["taxamt"],
        freight=h["freight"],
        total_due=h["totaldue"],
        customer=customer,
        sales_person=sales_person,
        ship_to=ship_to,
        bill_to=bill_to,
        ship_method=h["ship_method_name"],
        items=items,
        inventory=inventory,
    )
