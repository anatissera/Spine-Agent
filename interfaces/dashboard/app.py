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
    """)
    st.divider()
    st.caption("Anthropic Hackathon 2026")

# ── Hero: short, punchy ─────────────────────────────────────────────────────
st.markdown("")
st.markdown(
    '<div class="hero-title">The AI that operates<br>your business.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-subtitle" style="max-width:520px">'
    'An autonomous agent that understands the structure of your business, '
    'not just the text. It queries, reasons, plans, acts, and learns.'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("")
st.markdown("")

# ── Live numbers (the wow factor) ───────────────────────────────────────────
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

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Orders Managed", f"{orders['cnt']:,}")
    c2.metric("Total Revenue", format_currency(orders['total']))
    c3.metric("Avg Order Value", format_currency(orders['avg']))
    c4.metric("Customers", f"{customers['cnt']:,}")
    c5.metric("Agent Skills", f"{skills['cnt']}")

    db_connected = True
except Exception as e:
    st.error(f"Database not connected: {e}")
    st.caption("Run `sudo docker compose up -d` to start the database.")
    db_connected = False

st.markdown("")
st.markdown("")

# ── Problem → Solution (two columns, very brief) ────────────────────────────
left, right = st.columns(2)

with left:
    st.markdown(
        '<div class="card card-accent-red">'
        '<div class="feature-title" style="color:#ef4444">The problem</div>'
        '<div class="feature-desc" style="font-size:0.9rem;line-height:1.7">'
        'Every business has one central object '
        '— an order, a deal, a case, a policy. '
        'It crosses every department. Today, a <strong>person</strong> is the glue: '
        'checking one system, copy-pasting into another, sending a message manually. '
        'The human is the integration layer.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with right:
    st.markdown(
        '<div class="card card-accent-blue">'
        '<div class="feature-title" style="color:#4f8ff7">SpineAgent</div>'
        '<div class="feature-desc" style="font-size:0.9rem;line-height:1.7">'
        'An agent that operates on the <strong>structural topology</strong> of the business. '
        'It knows the objects, relationships, states, and possible actions. '
        'The human stops being the relay and becomes the <strong>approver</strong>. '
        'Read is autonomous. Write needs your OK.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("")
st.markdown("")

# ── Three modes (tight, visual) ─────────────────────────────────────────────
st.markdown(
    f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;'
    f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px">Three modes of operation</div>',
    unsafe_allow_html=True,
)

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown(
        '<div class="feature-card card-accent-blue">'
        '<div class="feature-title" style="font-size:1.1rem">Assist</div>'
        '<div class="feature-desc">"What is the status of order 43659?"'
        '<br>Routes to the right skill, queries the spine, answers with real data.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        '<div class="feature-card card-accent-green">'
        '<div class="feature-title" style="font-size:1.1rem">Act</div>'
        '<div class="feature-desc">"Notify the customer their order shipped."'
        '<br>Plans the steps, executes reads, halts at writes for your approval.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        '<div class="feature-card card-accent-amber">'
        '<div class="feature-title" style="font-size:1.1rem">Monitor</div>'
        '<div class="feature-desc">No one needs to ask.'
        '<br>Scans for stale orders, anomalies, and escalations. Alerts before problems grow.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("")
st.markdown("")

# ── What makes it different (one line each) ─────────────────────────────────
st.markdown(
    f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;'
    f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px">What makes this different</div>',
    unsafe_allow_html=True,
)

d1, d2, d3 = st.columns(3)

with d1:
    st.markdown(
        '<div class="card" style="padding:20px">'
        f'<div style="color:{COLORS["primary"]};font-weight:700;font-size:0.95rem;margin-bottom:6px">Persistent memory</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem">Not a chat session. Every decision, action, and pattern '
        'is stored with vector embeddings. The agent gets smarter over time.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with d2:
    st.markdown(
        '<div class="card" style="padding:20px">'
        f'<div style="color:{COLORS["success"]};font-weight:700;font-size:0.95rem;margin-bottom:6px">Self-improving skills</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem">When the agent can\'t do something, it generates a new skill '
        'with Claude, validates it in a sandbox, and registers it. Institutional knowledge, codified.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with d3:
    st.markdown(
        '<div class="card" style="padding:20px">'
        f'<div style="color:{COLORS["warning"]};font-weight:700;font-size:0.95rem;margin-bottom:6px">Approval gate</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem">Read = autonomous. Write = needs your OK. '
        'Not a limitation. The trust mechanism that makes delegation safe and scalable.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("")
st.markdown("")

# ── Recent activity (if DB connected) ───────────────────────────────────────
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

# ── Built with (compact, at the bottom) ─────────────────────────────────────
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
    ("Docker Compose", "One-command setup\n+ auto-loaded demo data"),
]
for col, (name, detail) in zip([t1, t2, t3, t4, t5], tech):
    col.markdown(
        f'<div style="text-align:center;padding:12px 0">'
        f'<div style="color:{COLORS["text"]};font-weight:600;font-size:0.85rem">{name}</div>'
        f'<div style="color:{COLORS["text_dim"]};font-size:0.72rem;white-space:pre-line;margin-top:4px">{detail}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
