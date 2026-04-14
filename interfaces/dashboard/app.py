"""SpineAgent Dashboard — Landing + Overview.

Run with:  PYTHONPATH=. streamlit run interfaces/dashboard/app.py
"""

import streamlit as st
from interfaces.dashboard.helpers import inject_css, run_async, format_currency, COLORS

st.set_page_config(page_title="SpineAgent", page_icon="🦴", layout="wide", initial_sidebar_state="expanded")
inject_css()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### SpineAgent")
    st.caption("Operational Intelligence")
    st.divider()
    st.markdown("""
    **Pages**
    - Home — Overview
    - Chat — Talk to the agent
    - Spine Explorer — View orders
    - Monitor — Detect anomalies
    - Skills — Skill registry
    """)
    st.divider()
    st.caption("Anthropic Hackathon 2026")

# ── Hero Section ─────────────────────────────────────────────────────────────
st.markdown("")
st.markdown('<div class="hero-title">Your business runs on<br>one operational object.</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">'
    'SpineAgent is an autonomous AI that operates on the root entity of your business '
    '— the object with the highest density of cross-domain references. '
    'It observes, reasons, plans, and acts — while humans stay in control.'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("")

# ── Three modes ──────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        '<div class="feature-card card-accent-blue">'
        '<span class="feature-icon">Assist</span>'
        '<div class="feature-title">Mode: Assist</div>'
        '<div class="feature-desc">Ask questions about orders, customers, inventory. '
        'The agent queries the spine, activates the right skill, and responds with real data.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        '<div class="feature-card card-accent-green">'
        '<span class="feature-icon">Act</span>'
        '<div class="feature-title">Mode: Act</div>'
        '<div class="feature-desc">Give an objective. The agent decomposes it into a plan, '
        'executes read steps autonomously, and halts at write actions for your approval.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        '<div class="feature-card card-accent-amber">'
        '<span class="feature-icon">Monitor</span>'
        '<div class="feature-title">Mode: Monitor</div>'
        '<div class="feature-desc">Runs in the background. Detects stale orders, anomalies, '
        'and situations that need attention — before anyone asks.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── Key differentiator ──────────────────────────────────────────────────────
left, right = st.columns([2, 1])
with left:
    st.markdown(
        '<div class="card card-accent-blue">'
        '<div class="feature-title">The Spine: a structural abstraction</div>'
        '<div class="feature-desc" style="max-width:100%">'
        'Unlike generic LLM wrappers, SpineAgent operates on the <strong>topological structure</strong> '
        'of your business. It knows what objects exist, how they relate, what state they\'re in, '
        'and what actions are possible. For this demo, the spine object is a <strong>SalesOrder</strong> '
        'from AdventureWorks — unifying Sales, Production, Person, and Purchasing domains.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with right:
    st.markdown(
        '<div class="card card-accent-green">'
        '<div class="feature-title">AutoSkill: self-improving</div>'
        '<div class="feature-desc" style="max-width:100%">'
        'When the agent needs a capability it doesn\'t have, it generates a new skill '
        'using Claude — validates it, persists it, and uses it. The skill registry '
        'becomes codified institutional knowledge.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── Live Dashboard ───────────────────────────────────────────────────────────
st.markdown("### Live Dashboard")

try:
    from agent.db import get_connection

    async def get_stats():
        async with await get_connection() as conn:
            orders = await (await conn.execute(
                "SELECT count(*) as cnt, round(sum(totaldue)::numeric, 2) as total FROM sales.salesorderheader"
            )).fetchone()
            customers = await (await conn.execute("SELECT count(*) as cnt FROM sales.customer")).fetchone()
            products = await (await conn.execute("SELECT count(*) as cnt FROM production.product")).fetchone()
            skills = await (await conn.execute(
                "SELECT count(*) as cnt FROM spine_agent.skills WHERE enabled = true"
            )).fetchone()
            pending = await (await conn.execute(
                "SELECT count(*) as cnt FROM spine_agent.pending_approvals WHERE status = 'pending'"
            )).fetchone()
            context = await (await conn.execute("SELECT count(*) as cnt FROM spine_agent.context_entries")).fetchone()
        return orders, customers, products, skills, pending, context

    orders, customers, products, skills, pending, context = run_async(get_stats())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Orders", f"{orders['cnt']:,}")
    c2.metric("Revenue", format_currency(orders['total']))
    c3.metric("Customers", f"{customers['cnt']:,}")
    c4.metric("Products", f"{products['cnt']:,}")
    c5.metric("Active Skills", f"{skills['cnt']}")
    c6.metric("Context Entries", f"{context['cnt']}")

    st.markdown("")

    # Recent activity
    from agent.context_store import search_structured
    recent = run_async(search_structured(limit=5))
    if recent:
        st.markdown("**Recent Agent Activity**")
        for entry in recent[:5]:
            content = entry.get("content", {})
            if isinstance(content, dict):
                summary = content.get("message", content.get("user_message", str(content)[:80]))
            else:
                summary = str(content)[:80]
            st.markdown(
                f'<div class="card" style="padding:12px 20px;margin-bottom:8px">'
                f'<span style="color:{COLORS["primary"]};font-weight:600;font-size:0.8rem">{entry["entry_type"]}</span>'
                f' <span style="color:{COLORS["text_dim"]};font-size:0.75rem;float:right">{str(entry["created_at"])[:19]}</span>'
                f'<br><span style="color:{COLORS["text_muted"]};font-size:0.85rem">{summary}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No agent activity yet. Head to Chat to start interacting.")

except Exception as e:
    st.error(f"Database connection error: {e}")
    st.info("Make sure Docker is running: `sudo docker compose up -d`")
