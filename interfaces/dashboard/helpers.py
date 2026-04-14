"""Shared helpers and design system for the SpineAgent dashboard."""

from __future__ import annotations

import asyncio
import streamlit as st

# ── Async bridge ─────────────────────────────────────────────────────────────
_loop = None


def run_async(coro):
    """Run an async coroutine from synchronous Streamlit code."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)


# ── Design tokens ────────────────────────────────────────────────────────────
COLORS = {
    "bg_primary": "#0a0f1e",
    "bg_card": "#111827",
    "bg_card_hover": "#1a2332",
    "border": "#1e293b",
    "primary": "#4f8ff7",
    "primary_muted": "#4f8ff733",
    "success": "#10b981",
    "success_muted": "#10b98133",
    "warning": "#f59e0b",
    "warning_muted": "#f59e0b33",
    "danger": "#ef4444",
    "danger_muted": "#ef444433",
    "text": "#f8fafc",
    "text_muted": "#94a3b8",
    "text_dim": "#64748b",
}

STATUS_CONFIG = {
    1: {"color": "#f59e0b", "label": "In Process", "icon": "hourglass_flowing_sand"},
    2: {"color": "#4f8ff7", "label": "Approved", "icon": "white_check_mark"},
    3: {"color": "#ef4444", "label": "Backordered", "icon": "warning"},
    4: {"color": "#64748b", "label": "Rejected", "icon": "x"},
    5: {"color": "#10b981", "label": "Shipped", "icon": "package"},
    6: {"color": "#94a3b8", "label": "Cancelled", "icon": "no_entry_sign"},
}

ALERT_ICONS = {"WARNING": "warning", "HIGH": "red_circle", "CRITICAL": "rotating_light"}


# ── Formatting ───────────────────────────────────────────────────────────────


def format_currency(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


def status_badge_html(status: int) -> str:
    cfg = STATUS_CONFIG.get(status, {"color": "#64748b", "label": f"Unknown ({status})"})
    return (
        f'<span style="background:{cfg["color"]}22;color:{cfg["color"]};'
        f'border:1px solid {cfg["color"]}44;padding:4px 14px;border-radius:20px;'
        f'font-size:0.8rem;font-weight:600;letter-spacing:0.02em">'
        f'{cfg["label"]}</span>'
    )


# ── Global CSS (call once per page) ─────────────────────────────────────────

GLOBAL_CSS = """
<style>
    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    /* ── Base ── */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1321 0%, #0a0f1e 100%);
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] { color: #cbd5e1; }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 20px;
        transition: border-color 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        border-color: #4f8ff744;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94a3b8;
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 16px;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        font-family: 'Plus Jakarta Sans', sans-serif;
        letter-spacing: 0.01em;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(79, 143, 247, 0.2);
    }

    /* ── Data frames ── */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #1e293b;
    }

    /* ── Expanders ── */
    [data-testid="stExpander"] {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 12px;
        overflow: hidden;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 20px;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a0f1e; }
    ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }

    /* ── Cards (custom class) ── */
    .card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
    }
    .card-accent-blue { border-left: 3px solid #4f8ff7; }
    .card-accent-green { border-left: 3px solid #10b981; }
    .card-accent-amber { border-left: 3px solid #f59e0b; }
    .card-accent-red { border-left: 3px solid #ef4444; }

    /* ── Hero section ── */
    .hero-title {
        font-size: 2.8rem;
        font-weight: 700;
        line-height: 1.15;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #f8fafc 0%, #4f8ff7 50%, #10b981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        font-size: 1.15rem;
        color: #94a3b8;
        line-height: 1.6;
        max-width: 640px;
    }

    /* ── Feature cards ── */
    .feature-card {
        background: linear-gradient(135deg, #11182700, #111827);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 28px;
        height: 100%;
        transition: border-color 0.2s ease, transform 0.2s ease;
    }
    .feature-card:hover {
        border-color: #4f8ff744;
        transform: translateY(-2px);
    }
    .feature-icon {
        font-size: 1.5rem;
        margin-bottom: 12px;
        display: block;
    }
    .feature-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #f8fafc;
        margin-bottom: 8px;
    }
    .feature-desc {
        font-size: 0.85rem;
        color: #94a3b8;
        line-height: 1.5;
    }

    /* ── Hide Streamlit branding ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""


def inject_css():
    """Inject the global CSS into the current page. Call at the top of each page."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
