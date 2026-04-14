"""Skill: get detailed customer information for a sales order or customer ID."""

from typing import Any

from skills.base_skill import BaseSkill


class GetCustomerInfo(BaseSkill):
    name = "get_customer_info"
    description = "Get detailed customer information including name, email, phone, and store — by order or customer ID"
    domain = "person"

    def get_spec(self) -> dict[str, Any]:
        return {
            "inputs": {
                "order_id": {"type": "integer", "required": False},
                "customer_id": {"type": "integer", "required": False},
            },
            "outputs": ["customer_id", "name", "email", "phone", "store_name"],
            "dependencies": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        order_id = kwargs.get("order_id")
        customer_id = kwargs.get("customer_id")

        if order_id:
            from agent.spine import get_spine
            spine = await get_spine(order_id)
            if spine is None:
                return {"success": False, "error": f"Order {order_id} not found"}
            c = spine.customer
            return {
                "success": True,
                "customer_id": c.customer_id,
                "person_id": c.person_id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "phone": c.phone,
                "store_id": c.store_id,
                "store_name": c.store_name,
            }

        if customer_id:
            return await self._query_by_customer_id(customer_id)

        return {"success": False, "error": "Provide either order_id or customer_id"}

    async def _query_by_customer_id(self, customer_id: int) -> dict[str, Any]:
        from agent.db import get_connection

        async with await get_connection() as conn:
            row = await (
                await conn.execute(
                    """
                    SELECT c.customerid, c.personid, c.storeid,
                           p.firstname, p.lastname,
                           ea.emailaddress, pp.phonenumber,
                           s.name AS store_name
                    FROM sales.customer c
                    LEFT JOIN person.person p       ON p.businessentityid  = c.personid
                    LEFT JOIN person.emailaddress ea ON ea.businessentityid = c.personid
                    LEFT JOIN person.personphone pp  ON pp.businessentityid = c.personid
                    LEFT JOIN sales.store s          ON s.businessentityid  = c.storeid
                    WHERE c.customerid = %(cid)s
                    LIMIT 1
                    """,
                    {"cid": customer_id},
                )
            ).fetchone()

        if row is None:
            return {"success": False, "error": f"Customer {customer_id} not found"}

        return {
            "success": True,
            "customer_id": row["customerid"],
            "person_id": row["personid"],
            "first_name": row["firstname"],
            "last_name": row["lastname"],
            "email": row["emailaddress"],
            "phone": row["phonenumber"],
            "store_id": row["storeid"],
            "store_name": row["store_name"],
        }
