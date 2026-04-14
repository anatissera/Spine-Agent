"""Integration tests for agent.spine — requires a running AdventureWorks DB."""

import pytest

from agent.spine import SpineOrder, get_spine


@pytest.mark.asyncio
async def test_get_spine_existing_order():
    """Order 43659 exists in AdventureWorks and should return a full SpineOrder."""
    spine = await get_spine(43659)
    assert spine is not None
    assert isinstance(spine, SpineOrder)
    assert spine.sales_order_id == 43659
    assert spine.spine_object_id == "SalesOrder:43659"
    assert spine.status in range(1, 7)
    assert spine.status_label != ""
    assert spine.total_due > 0
    # Customer must be populated
    assert spine.customer.customer_id > 0
    # Must have at least 1 line item
    assert len(spine.items) > 0
    # Each item must have a product name
    for item in spine.items:
        assert item.product_name
        assert item.unit_price >= 0


@pytest.mark.asyncio
async def test_get_spine_nonexistent_order():
    """A nonexistent order should return None."""
    spine = await get_spine(99_999_999)
    assert spine is None


@pytest.mark.asyncio
async def test_spine_json_serializable():
    """The spine model should serialize to JSON cleanly."""
    spine = await get_spine(43659)
    assert spine is not None
    data = spine.model_dump(mode="json")
    assert data["sales_order_id"] == 43659
    assert isinstance(data["items"], list)
    assert isinstance(data["customer"], dict)
