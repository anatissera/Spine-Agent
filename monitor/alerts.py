"""Alert generation and routing for SpineAgent Monitor mode.

Routes alerts to configured channels. Currently supports:
  - stdout (always, for CLI/logging)
  - context_store (persists alerts for future reference)
  - telegram (stub — will be wired to M3 Telegram MCP after merge)
"""

from __future__ import annotations

import json
from datetime import datetime

from agent.context_store import add_entry

# ── Alert formatting ─────────────────────────────────────────────────────────

LEVEL_PREFIX = {
    "WARNING": "⚠️",
    "HIGH": "🔴",
    "CRITICAL": "🚨",
}


def format_alert(alert: dict) -> str:
    """Format an alert dict into a human-readable string."""
    prefix = LEVEL_PREFIX.get(alert.get("level", "WARNING"), "⚠️")
    return f"{prefix} [{alert.get('level', 'WARNING')}] {alert.get('message', json.dumps(alert))}"


# ── Routing ──────────────────────────────────────────────────────────────────


async def route_alerts(alerts: list[dict]) -> dict:
    """Route a batch of alerts to all configured channels.

    Returns a summary dict with counts per channel.
    """
    if not alerts:
        return {"total": 0, "channels": {}}

    results = {
        "total": len(alerts),
        "timestamp": datetime.now().isoformat(),
        "channels": {},
    }

    # Always: stdout
    _route_stdout(alerts)
    results["channels"]["stdout"] = len(alerts)

    # Always: persist to context store
    persisted = await _route_context_store(alerts)
    results["channels"]["context_store"] = persisted

    # Future: Telegram (after M3 merge)
    # persisted_tg = await _route_telegram(alerts)
    # results["channels"]["telegram"] = persisted_tg

    return results


def _route_stdout(alerts: list[dict]) -> None:
    """Print alerts to stdout."""
    print(f"\n{'='*60}")
    print(f"  SpineAgent Monitor — {len(alerts)} alert(s) detected")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    for alert in alerts:
        print(f"  {format_alert(alert)}")
    print(f"{'='*60}\n")


async def _route_context_store(alerts: list[dict]) -> int:
    """Persist alerts as context entries for future reference."""
    count = 0
    for alert in alerts:
        order_id = alert.get("order_id")
        if order_id:
            await add_entry(
                spine_object_id=f"SalesOrder:{order_id}",
                entry_type="action_result",
                content={
                    "alert_type": alert.get("type"),
                    "alert_level": alert.get("level"),
                    "message": alert.get("message"),
                    "detected_at": datetime.now().isoformat(),
                },
                source="agent",
            )
            count += 1
    return count


# Stub for Telegram integration (M3 merge)
# async def _route_telegram(alerts: list[dict]) -> int:
#     """Send alerts via Telegram MCP server."""
#     from mcp_servers.telegram.server import send_alert
#     count = 0
#     for alert in alerts:
#         try:
#             await send_alert(
#                 alert_text=format_alert(alert),
#                 approval_id=...,  # needs approval gate
#                 level=alert.get("level", "WARNING"),
#             )
#             count += 1
#         except Exception:
#             pass
#     return count
