"""Skill: detect orders that have been in their current status too long."""

from typing import Any

from skills.base_skill import BaseSkill


class DetectStaleOrders(BaseSkill):
    name = "detect_stale_orders"
    description = "Detect sales orders that have been stale (no activity) beyond expected thresholds"
    domain = "sales"

    def get_spec(self) -> dict[str, Any]:
        return {
            "inputs": {"limit": {"type": "integer", "required": False, "default": 20}},
            "outputs": ["alerts", "alert_count"],
            "dependencies": [],
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        from monitor.rules import detect_stale_orders

        limit = kwargs.get("limit", 20)
        alerts = await detect_stale_orders(limit=limit)

        return {
            "success": True,
            "alert_count": len(alerts),
            "alerts": alerts,
        }
