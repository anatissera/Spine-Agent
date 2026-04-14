"""Skill: list all items in a sales order with product details."""

from typing import Any

from skills.base_skill import BaseSkill


class ListOrderItems(BaseSkill):
    name = "list_order_items"
    description = "List all items in a sales order with product names, quantities, and pricing"
    domain = "sales"

    def get_spec(self) -> dict[str, Any]:
        return {
            "inputs": {"order_id": {"type": "integer", "required": True}},
            "outputs": ["items", "item_count", "subtotal"],
            "dependencies": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        from agent.spine import get_spine

        order_id = kwargs["order_id"]
        spine = await get_spine(order_id)
        if spine is None:
            return {"success": False, "error": f"Order {order_id} not found"}

        return {
            "success": True,
            "order_id": order_id,
            "item_count": len(spine.items),
            "items": [item.model_dump(mode="json") for item in spine.items],
            "subtotal": str(spine.subtotal),
        }
