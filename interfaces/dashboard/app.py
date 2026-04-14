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
    - Home
    - Chat
    - Spine Explorer
    - Monitor
    - Skills
    - Activity
    """)
    st.divider()
    st.caption("Anthropic Hackathon 2026")

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("")
st.markdown(
    '<div class="hero-title">Your business runs on<br>one operational object.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-subtitle" style="max-width:560px">'
    'A multi-agent system that understands the structural topology of your business. '
    'It queries, reasons, plans, learns, and acts '
    '— while humans stay in control.'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("")
st.markdown("")

# ── Problem → Solution ──────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.markdown(
        '<div class="card card-accent-red">'
        '<div class="feature-title" style="color:#ef4444">The problem</div>'
        '<div class="feature-desc" style="font-size:0.88rem;line-height:1.7">'
        'Every organization has one entity that concentrates cross-domain complexity '
        '— an order, a deal, a case, a policy. It touches Sales, Production, Purchasing, '
        'Customer Service, Logistics. Today, <strong>people</strong> are the integration layer: '
        'they check status in one system, look up a customer in another, verify inventory in a third, '
        'then manually relay the result. This doesn\'t scale, it\'s error-prone, '
        'and institutional knowledge walks out the door when someone leaves.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with right:
    st.markdown(
        '<div class="card card-accent-blue">'
        '<div class="feature-title" style="color:#4f8ff7">SpineAgent</div>'
        '<div class="feature-desc" style="font-size:0.88rem;line-height:1.7">'
        'A multi-agent system built on the concept of the <strong>operational spine</strong> '
        '— the root entity with the highest density of cross-domain references. '
        'SpineAgent reconstructs the unified state of this object from multiple sources, '
        'reasons over its relationships, plans sequences of actions, '
        'and executes them autonomously. '
        'The human shifts from being the <strong>relay</strong> to being the <strong>approver</strong>. '
        'Every read operation is autonomous. Every write operation requires explicit approval.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("")
st.markdown("")

# ── Three modes ──────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;'
    f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px">Three modes of operation</div>',
    unsafe_allow_html=True,
)

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown(
        '<div class="feature-card card-accent-blue">'
        '<div class="feature-title" style="font-size:1.05rem">Assist</div>'
        '<div class="feature-desc" style="line-height:1.6">'
        'An operator asks a question. The router classifies intent and domain, '
        'activates the matching skill, queries the spine, enriches with context store history, '
        'and generates a response grounded in real data. '
        'No hallucination — every answer is backed by a SQL query.'
        '</div></div>',
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        '<div class="feature-card card-accent-green">'
        '<div class="feature-title" style="font-size:1.05rem">Act</div>'
        '<div class="feature-desc" style="line-height:1.6">'
        'An operator gives an objective. The planner decomposes it into an ordered chain of skills '
        'with READ/WRITE classification. The executor runs READ steps autonomously, '
        'then halts at the first WRITE with a pending approval containing full context. '
        'The human reviews, approves or rejects. The agent proceeds or stands down.'
        '</div></div>',
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        '<div class="feature-card card-accent-amber">'
        '<div class="feature-title" style="font-size:1.05rem">Monitor</div>'
        '<div class="feature-desc" style="line-height:1.6">'
        'A scheduled process scans the spine continuously for anomalies: '
        'orders stuck beyond configurable thresholds, overdue shipments, inventory gaps. '
        'When something deviates from expected state, the agent generates an alert '
        'and routes it to the right channel — before anyone needs to ask.'
        '</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("")
st.markdown("")

# ── What makes it different ─────────────────────────────────────────────────
st.markdown(
    f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;'
    f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px">What makes this different</div>',
    unsafe_allow_html=True,
)

d1, d2, d3 = st.columns(3)

with d1:
    st.markdown(
        '<div class="card" style="padding:20px">'
        f'<div style="color:{COLORS["primary"]};font-weight:700;font-size:0.95rem;margin-bottom:6px">'
        'Persistent context store</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem;line-height:1.6">'
        'Every decision, action result, and state snapshot is stored in PostgreSQL '
        'with vector embeddings for semantic retrieval. The agent accumulates institutional '
        'memory that compounds over time.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with d2:
    st.markdown(
        '<div class="card" style="padding:20px">'
        f'<div style="color:{COLORS["success"]};font-weight:700;font-size:0.95rem;margin-bottom:6px">'
        'AutoSkill generation</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem;line-height:1.6">'
        'When no skill matches a request, Claude generates Python code for a new one, '
        'validates it in a sandbox, and persists it in the registry. '
        'The skill library becomes codified operational knowledge.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with d3:
    st.markdown(
        '<div class="card" style="padding:20px">'
        f'<div style="color:{COLORS["warning"]};font-weight:700;font-size:0.95rem;margin-bottom:6px">'
        'Human-in-the-loop gate</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem;line-height:1.6">'
        'Read = autonomous. Write = requires explicit approval. '
        'Not a transitional limitation — the permanent trust mechanism '
        'that allows safe, incremental delegation of operational work.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("")
st.markdown("")

# ── Live system numbers ──────────────────────────────────────────────────────
try:
    from agent.db import get_connection

    async def get_stats():
        async with await get_connection() as conn:
            orders = await (await conn.execute(
                "SELECT count(*) as cnt, round(sum(totaldue)::numeric, 2) as total, "
                "round(avg(totaldue)::numeric, 2) as avg FROM sales.salesorderheader"
            )).fetchone()
            customers = await (await conn.execute("SELECT count(*) as cnt FROM sales.customer")).fetchone()
            products = await (await conn.execute("SELECT count(*) as cnt FROM production.product")).fetchone()
            skills = await (await conn.execute(
                "SELECT count(*) as cnt FROM spine_agent.skills WHERE enabled = true"
            )).fetchone()
            context = await (await conn.execute("SELECT count(*) as cnt FROM spine_agent.context_entries")).fetchone()
        return orders, customers, products, skills, context

    orders, customers, products, skills, context = run_async(get_stats())

    st.markdown(
        f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;'
        f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px">Live system</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Orders", f"{orders['cnt']:,}")
    c2.metric("Revenue", format_currency(orders['total']))
    c3.metric("Avg Order", format_currency(orders['avg']))
    c4.metric("Customers", f"{customers['cnt']:,}")
    c5.metric("Skills", f"{skills['cnt']}")

    db_connected = True
except Exception as e:
    st.error(f"Database not connected: {e}")
    st.caption("Run `sudo docker compose up -d` to start the database.")
    db_connected = False

st.markdown("")

# ── Learn more (expandable deep dive) ───────────────────────────────────────
with st.expander("Architecture deep dive"):
    st.markdown(
        f'<div style="max-width:780px">'

        # Multi-agent
        f'<div class="card card-accent-blue" style="margin-bottom:16px">'
        f'<div style="color:{COLORS["text"]};font-weight:600;font-size:0.95rem;margin-bottom:8px">'
        'Multi-agent architecture</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.85rem;line-height:1.7">'
        'SpineAgent is not a single prompt chain. It is a system of specialized components '
        'that collaborate: a <strong>router</strong> classifies intent and selects the execution mode. '
        'A <strong>planner</strong> decomposes complex objectives into skill chains using Claude. '
        'An <strong>executor</strong> runs the chain with autonomous/gated classification per step. '
        'A <strong>monitor</strong> runs independently on a schedule. '
        'And the <strong>AutoSkill loop</strong> generates, validates, and registers new capabilities. '
        'Each component is independently testable and replaceable.</div></div>'

        # Spine
        f'<div class="card" style="margin-bottom:16px">'
        f'<div style="color:{COLORS["text"]};font-weight:600;font-size:0.95rem;margin-bottom:8px">'
        'The Spine Object</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.85rem;line-height:1.7">'
        'A unified Pydantic model that reconstructs a SalesOrder from 10+ tables '
        'across 4 schemas (Sales, Production, Person, Purchasing) via 3 parameterized SQL queries. '
        'Customer info, addresses, line items with margins, inventory levels per product — '
        'one call, complete cross-domain context.</div></div>'

        # Context Store
        f'<div class="card" style="margin-bottom:16px">'
        f'<div style="color:{COLORS["text"]};font-weight:600;font-size:0.95rem;margin-bottom:8px">'
        'Context Store</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.85rem;line-height:1.7">'
        'PostgreSQL + pgvector. Every decision, action result, pattern, and state snapshot '
        'is stored with a 1536-dim vector embedding. Supports both semantic search '
        '(\"find similar situations\") and structured queries (\"all actions on order #43659\"). '
        'This is not session memory — it is persistent institutional knowledge.</div></div>'

        # Approval Gate
        f'<div class="card" style="margin-bottom:16px">'
        f'<div style="color:{COLORS["text"]};font-weight:600;font-size:0.95rem;margin-bottom:8px">'
        'Approval Gate</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.85rem;line-height:1.7">'
        'Every write action creates a pending approval record in PostgreSQL with full context: '
        'what the action is, why it was proposed, the data behind it, and a 2-hour expiry. '
        'Approvals appear as notifications on the Activity page and as banners in Chat. '
        'The human approves, rejects, or lets it expire. The agent proceeds or stands down.</div></div>'

        # Demo
        f'<div class="card" style="margin-bottom:0">'
        f'<div style="color:{COLORS["text"]};font-weight:600;font-size:0.95rem;margin-bottom:8px">'
        'This demo</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.85rem;line-height:1.7">'
        'Running on <strong>AdventureWorks OLTP</strong> — 31,000+ orders, 19,000+ customers, '
        '500+ products. The spine object is a SalesOrder. '
        'Every response in this dashboard comes from live SQL queries against real data, '
        'processed by Claude via the Anthropic API. Nothing is mocked. '
        'Integrations with Tiendanube (e-commerce) and Telegram (messaging) via MCP servers.</div></div>'

        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("")

# ── Recent activity ──────────────────────────────────────────────────────────
if db_connected:
    from agent.context_store import search_structured
    recent = run_async(search_structured(limit=5))
    if recent:
        st.markdown(
            f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;'
            f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px">Recent agent activity</div>',
            unsafe_allow_html=True,
        )
        for entry in recent[:4]:
            content = entry.get("content", {})
            if isinstance(content, dict):
                summary = content.get("message", content.get("user_message", str(content)[:80]))
            else:
                summary = str(content)[:80]
            st.markdown(
                f'<div class="card" style="padding:10px 20px;margin-bottom:6px">'
                f'<span style="color:{COLORS["primary"]};font-weight:600;font-size:0.75rem">{entry["entry_type"]}</span>'
                f' <span style="color:{COLORS["text_dim"]};font-size:0.7rem;float:right">{str(entry["created_at"])[:19]}</span>'
                f'<br><span style="color:{COLORS["text_muted"]};font-size:0.8rem">{summary}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.markdown("")
st.markdown("")

# ── Built with ──────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;'
    f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px">Built with</div>',
    unsafe_allow_html=True,
)

t1, t2, t3, t4, t5 = st.columns(5)
tech = [
    ("Claude API", "Routing, planning,\nresponse generation"),
    ("PostgreSQL 16", "AdventureWorks OLTP\n+ pgvector embeddings"),
    ("MCP Protocol", "Tiendanube e-commerce\n+ Telegram Bot"),
    ("Python async", "Pydantic models,\npsycopg3, APScheduler"),
    ("Docker Compose", "One-command setup\n+ auto-loaded data"),
]
for col, (name, detail) in zip([t1, t2, t3, t4, t5], tech):
    col.markdown(
        f'<div style="text-align:center;padding:12px 0">'
        f'<div style="color:{COLORS["text"]};font-weight:600;font-size:0.85rem">{name}</div>'
        f'<div style="color:{COLORS["text_dim"]};font-size:0.72rem;white-space:pre-line;margin-top:4px">{detail}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
