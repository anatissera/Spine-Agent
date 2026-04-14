"""Skill: query the current status of a sales order."""

from typing import Any

from skills.base_skill import BaseSkill


class QueryOrderStatus(BaseSkill):
    name = "query_order_status"
    description = "Query the current status of a sales order including dates, totals, and customer info"
    domain = "sales"

    def get_spec(self) -> dict[str, Any]:
        return {
            "inputs": {"order_id": {"type": "integer", "required": True}},
            "outputs": ["status", "order_date", "total_due", "customer_name", "item_count"],
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
            "order_id": spine.sales_order_id,
            "status": spine.status_label,
            "order_date": spine.order_date.isoformat(),
            "due_date": spine.due_date.isoformat(),
            "ship_date": spine.ship_date.isoformat() if spine.ship_date else None,
            "total_due": str(spine.total_due),
            "customer_name": f"{spine.customer.first_name or ''} {spine.customer.last_name or ''}".strip(),
            "item_count": len(spine.items),
            "online_order": spine.online_order,
        }
