"""Integration tests for agent.context_store — requires a running DB with spine_agent schema."""

import pytest

from agent.context_store import add_entry, get_entries_for_spine, search_semantic, search_structured


@pytest.mark.asyncio
async def test_add_and_search_structured():
    """Insert an entry and retrieve it by structured search."""
    entry_id = await add_entry(
        spine_object_id="SalesOrder:99999",
        entry_type="state_snapshot",
        content={"status": "test", "note": "integration test entry"},
        source="system",
    )
    assert entry_id > 0

    results = await search_structured(spine_object_id="SalesOrder:99999")
    assert len(results) >= 1
    found = [r for r in results if r["id"] == entry_id]
    assert len(found) == 1
    assert found[0]["entry_type"] == "state_snapshot"


@pytest.mark.asyncio
async def test_semantic_search():
    """Semantic search should return entries (at least the one we inserted)."""
    await add_entry(
        spine_object_id="SalesOrder:88888",
        entry_type="decision",
        content={"action": "shipped order", "reason": "all items ready"},
        source="agent",
    )
    results = await search_semantic("shipped order items ready", spine_object_id="SalesOrder:88888")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_get_entries_for_spine():
    """Convenience function should return entries for a given spine object."""
    sid = "SalesOrder:77777"
    await add_entry(spine_object_id=sid, entry_type="rule", content={"rule": "always confirm"}, source="human")
    entries = await get_entries_for_spine(sid)
    assert len(entries) >= 1
    assert all(e["spine_object_id"] == sid for e in entries)
