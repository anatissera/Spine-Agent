"""Skill: check inventory levels for a product or all products in an order."""

from typing import Any

from skills.base_skill import BaseSkill


class CheckInventory(BaseSkill):
    name = "check_inventory"
    description = "Check current inventory levels for a product or all products in an order"
    domain = "production"

    def get_spec(self) -> dict[str, Any]:
        return {
            "inputs": {
                "product_id": {"type": "integer", "required": False},
                "order_id": {"type": "integer", "required": False},
            },
            "outputs": ["products", "total_quantity", "in_stock"],
            "dependencies": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        product_id = kwargs.get("product_id")
        order_id = kwargs.get("order_id")

        if order_id:
            from agent.spine import get_spine
            spine = await get_spine(order_id)
            if spine is None:
                return {"success": False, "error": f"Order {order_id} not found"}
            return {
                "success": True,
                "order_id": order_id,
                "products": [inv.model_dump() for inv in spine.inventory],
            }

        if product_id:
            return await self._query_product(product_id)

        return {"success": False, "error": "Provide either product_id or order_id"}

    async def _query_product(self, product_id: int) -> dict[str, Any]:
        from agent.db import get_connection

        async with await get_connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT pi.productid, prod.name, prod.safetystocklevel,
                           prod.reorderpoint, pi.quantity, pi.shelf, pi.bin,
                           loc.name AS location_name
                    FROM production.productinventory pi
                    JOIN production.product prod ON prod.productid = pi.productid
                    JOIN production.location loc  ON loc.locationid = pi.locationid
                    WHERE pi.productid = %(pid)s
                    ORDER BY loc.name
                    """,
                    {"pid": product_id},
                )
            ).fetchall()

        if not rows:
            return {"success": False, "error": f"No inventory for product {product_id}"}

        total = sum(r["quantity"] for r in rows)
        return {
            "success": True,
            "product_id": product_id,
            "product_name": rows[0]["name"],
            "total_quantity": total,
            "safety_stock_level": rows[0]["safetystocklevel"],
            "reorder_point": rows[0]["reorderpoint"],
            "in_stock": total > 0,
            "locations": [
                {
                    "name": r["location_name"],
                    "quantity": r["quantity"],
                    "shelf": r["shelf"],
                    "bin": r["bin"],
                }
                for r in rows
            ],
        }
