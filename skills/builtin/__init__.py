"""Built-in skills for SpineAgent."""

from skills.base_skill import BaseSkill
from skills.builtin.check_inventory import CheckInventory
from skills.builtin.get_customer_info import GetCustomerInfo
from skills.builtin.list_order_items import ListOrderItems
from skills.builtin.query_order_status import QueryOrderStatus


def get_all_builtin_skills() -> list[BaseSkill]:
    """Return instances of all builtin skills for auto-registration."""
    return [
        QueryOrderStatus(),
        GetCustomerInfo(),
        ListOrderItems(),
        CheckInventory(),
    ]
