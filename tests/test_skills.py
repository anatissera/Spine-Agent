"""Integration tests for skills — requires a running DB with AdventureWorks + spine_agent schema."""

import pytest

from skills.builtin.check_inventory import CheckInventory
from skills.builtin.get_customer_info import GetCustomerInfo
from skills.builtin.list_order_items import ListOrderItems
from skills.builtin.query_order_status import QueryOrderStatus
from skills.registry import SkillRegistry


ORDER_ID = 43659  # Known order in AdventureWorks


@pytest.mark.asyncio
async def test_query_order_status():
    skill = QueryOrderStatus()
    result = await skill.execute(order_id=ORDER_ID)
    assert result["success"] is True
    assert result["order_id"] == ORDER_ID
    assert result["status"] != ""
    assert int(result["item_count"]) > 0


@pytest.mark.asyncio
async def test_get_customer_info_by_order():
    skill = GetCustomerInfo()
    result = await skill.execute(order_id=ORDER_ID)
    assert result["success"] is True
    assert result["customer_id"] > 0


@pytest.mark.asyncio
async def test_list_order_items():
    skill = ListOrderItems()
    result = await skill.execute(order_id=ORDER_ID)
    assert result["success"] is True
    assert len(result["items"]) > 0


@pytest.mark.asyncio
async def test_check_inventory_by_order():
    skill = CheckInventory()
    result = await skill.execute(order_id=ORDER_ID)
    assert result["success"] is True
    assert "products" in result


@pytest.mark.asyncio
async def test_skill_registry():
    registry = SkillRegistry()
    await registry.ensure_builtin_skills()

    # All 4 skills should be registered
    all_skills = await registry.list_all()
    assert len(all_skills) >= 4

    # Search by domain
    sales_skills = await registry.search_by_domain("sales")
    assert len(sales_skills) >= 2  # query_order_status + list_order_items

    # Get by name
    skill = await registry.get("query_order_status")
    assert skill is not None
    assert skill.name == "query_order_status"
