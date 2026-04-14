"""Shared helpers for the Streamlit dashboard."""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import Any, Callable

# Streamlit is synchronous — wrap all async calls through this helper.
_loop = None


def run_async(coro):
    """Run an async coroutine from synchronous Streamlit code."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)


def format_currency(value) -> str:
    """Format a numeric value as currency."""
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


STATUS_COLORS = {
    1: ("#FFA726", "In Process"),   # Orange
    2: ("#42A5F5", "Approved"),     # Blue
    3: ("#EF5350", "Backordered"),  # Red
    4: ("#78909C", "Rejected"),     # Grey
    5: ("#66BB6A", "Shipped"),      # Green
    6: ("#BDBDBD", "Cancelled"),    # Light grey
}


def status_badge(status: int) -> str:
    """Return an HTML badge for an order status."""
    color, label = STATUS_COLORS.get(status, ("#999", f"Unknown ({status})"))
    return f'<span style="background:{color};color:white;padding:2px 10px;border-radius:12px;font-size:0.85em;font-weight:600">{label}</span>'


ALERT_ICONS = {
    "WARNING": "⚠️",
    "HIGH": "🔴",
    "CRITICAL": "🚨",
}
