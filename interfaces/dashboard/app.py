"""SpineAgent Dashboard — main entry point.

Run with:
    PYTHONPATH=. streamlit run interfaces/dashboard/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="SpineAgent",
    page_icon="🦴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Clean header */
    .block-container { padding-top: 2rem; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea22, #764ba222);
        border: 1px solid #667eea44;
        border-radius: 12px;
        padding: 16px;
    }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        border: 1px solid #e0e0e044;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e, #16213e);
    }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }

    /* Tables */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* Status badges */
    .status-shipped { background: #66BB6A; color: white; padding: 2px 10px; border-radius: 12px; font-weight: 600; }
    .status-processing { background: #FFA726; color: white; padding: 2px 10px; border-radius: 12px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🦴 SpineAgent")
    st.markdown("*Operational intelligence for your business*")
    st.divider()
    st.markdown("""
    **Modes:**
    - 💬 **Assist** — Ask questions
    - ⚡ **Act** — Execute plans
    - 👁️ **Monitor** — Detect anomalies
    - 🧠 **AutoSkill** — Generate new skills
    """)
    st.divider()
    st.caption("Hackathon 2026 — Anthropic")

# ── Home Page ────────────────────────────────────────────────────────────────
st.title("🦴 SpineAgent Dashboard")
st.markdown("*Autonomous agent operating on the root operational object of your business*")

# Quick stats
from interfaces.dashboard.helpers import run_async, format_currency

try:
    from agent.db import get_connection

    async def get_stats():
        async with await get_connection() as conn:
            orders = await (await conn.execute(
                "SELECT count(*) as cnt, round(sum(totaldue)::numeric, 2) as total FROM sales.salesorderheader"
            )).fetchone()
            customers = await (await conn.execute(
                "SELECT count(*) as cnt FROM sales.customer"
            )).fetchone()
            products = await (await conn.execute(
                "SELECT count(*) as cnt FROM production.product"
            )).fetchone()
            context = await (await conn.execute(
                "SELECT count(*) as cnt FROM spine_agent.context_entries"
            )).fetchone()
            skills = await (await conn.execute(
                "SELECT count(*) as cnt FROM spine_agent.skills WHERE enabled = true"
            )).fetchone()
            approvals = await (await conn.execute(
                "SELECT count(*) as cnt FROM spine_agent.pending_approvals WHERE status = 'pending'"
            )).fetchone()
        return orders, customers, products, context, skills, approvals

    orders, customers, products, context, skills, approvals = run_async(get_stats())

    st.markdown("### Overview")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Orders", f"{orders['cnt']:,}")
    col2.metric("Revenue", format_currency(orders['total']))
    col3.metric("Customers", f"{customers['cnt']:,}")
    col4.metric("Products", f"{products['cnt']:,}")
    col5.metric("Skills", f"{skills['cnt']}")
    col6.metric("Pending Approvals", f"{approvals['cnt']}")

    st.divider()

    # Recent context entries
    st.markdown("### Recent Agent Activity")
    from agent.context_store import search_structured
    recent = run_async(search_structured(limit=10))
    if recent:
        for entry in recent[:5]:
            with st.container():
                cols = st.columns([1, 3, 1])
                cols[0].markdown(f"**{entry['entry_type']}**")
                content = entry.get('content', {})
                if isinstance(content, dict):
                    summary = content.get('message', content.get('user_message', str(content)[:100]))
                else:
                    summary = str(content)[:100]
                cols[1].markdown(summary)
                cols[2].caption(str(entry['created_at'])[:19])
    else:
        st.info("No agent activity yet. Try the Chat page to interact with the agent!")

    st.divider()

    # Quick monitor check
    st.markdown("### Monitor Alerts")
    from monitor.rules import detect_stale_orders
    alerts = run_async(detect_stale_orders(limit=5))
    if alerts:
        st.warning(f"**{len(alerts)}+ stale orders detected**")
        for a in alerts[:3]:
            st.markdown(f"- 🔴 Order **#{a['order_id']}**: {a['status_label']} for {a['hours_stale']:.0f}h — {a['customer_name']}")
        st.page_link("pages/3_Monitor.py", label="View all alerts →")
    else:
        st.success("No anomalies detected")

except Exception as e:
    st.error(f"Database connection error: {e}")
    st.info("Make sure Docker is running: `sudo docker compose up -d`")
