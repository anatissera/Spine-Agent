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

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("")
st.markdown('<div class="hero-title">Every business runs on<br>one operational object.</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="hero-subtitle">'
    'An order. A deal. A case. A policy. A project. '
    'Whatever you call it, there is always one entity at the center of your business '
    'that crosses every functional area, drags work through the organization, '
    'and concentrates the highest density of cross-domain relationships.'
    '<br><br>'
    'Today, a <strong>human</strong> is the glue that holds it together. '
    'They check the order status in one system, look up the customer in another, '
    'verify inventory in a third, then copy-paste the result into a message they send manually. '
    'They are the relay between areas. The walking integration layer.'
    '<br><br>'
    '<strong>SpineAgent replaces the relay with an agent.</strong> '
    'An agent that understands the structure of your business, reasons about it, '
    'plans sequences of actions, and executes them autonomously '
    '— while the human stays in control as the approver, not the middleman.'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("")
st.markdown("")

# ── What this is / What this is NOT ─────────────────────────────────────────

st.markdown("### What SpineAgent is")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        '<div class="feature-card card-accent-blue">'
        '<div class="feature-title">Active, stateful, self-improving</div>'
        '<div class="feature-desc">Not a chatbot that forgets. SpineAgent accumulates business context over time. '
        'Every interaction enriches its memory. After weeks of use, it understands your business '
        'better than any new hire would.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        '<div class="feature-card card-accent-green">'
        '<div class="feature-title">Reasons over business topology</div>'
        '<div class="feature-desc">Not an LLM wrapper over free text. SpineAgent operates on the structural '
        'abstraction of your business: what objects exist, how they relate, what state they are in, '
        'and what actions are possible.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        '<div class="feature-card card-accent-amber">'
        '<div class="feature-title">Builds its own capabilities</div>'
        '<div class="feature-desc">When the agent encounters a task it can\'t handle, it doesn\'t fail silently. '
        'It generates a new skill using Claude, validates it, and adds it to its registry. '
        'The skill library becomes codified institutional knowledge.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("")

# ── Three modes ──────────────────────────────────────────────────────────────

st.markdown("### Three modes of operation")

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown(
        '<div class="feature-card card-accent-blue">'
        '<span class="feature-icon">Assist</span>'
        '<div class="feature-title">Ask anything</div>'
        '<div class="feature-desc">'
        '"What is the status of order 43659?" The agent routes the question to the right domain, '
        'queries the spine, and responds with real data from your systems. Not a search. A structured answer.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        '<div class="feature-card card-accent-green">'
        '<span class="feature-icon">Act</span>'
        '<div class="feature-title">Give an objective</div>'
        '<div class="feature-desc">'
        '"Notify the customer of order 43659 that their package shipped." The agent decomposes it into steps, '
        'executes read operations autonomously, and halts at the first write action for your explicit approval.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        '<div class="feature-card card-accent-amber">'
        '<span class="feature-icon">Monitor</span>'
        '<div class="feature-title">Proactive vigilance</div>'
        '<div class="feature-desc">'
        'No one needs to ask. The agent scans the spine periodically, detects orders stuck beyond thresholds, '
        'identifies anomalies, and generates alerts before a problem escalates. It watches so you don\'t have to.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("")

# ── The trust mechanism ──────────────────────────────────────────────────────

st.markdown("### The core principle: Read is autonomous, Write needs approval")

st.markdown(
    '<div class="card card-accent-red" style="max-width:800px">'
    '<div class="feature-desc" style="max-width:100%;font-size:0.9rem;line-height:1.7">'
    'This is not a transitional limitation. It is the permanent trust mechanism that makes delegation safe.'
    '<br><br>'
    'The agent can <strong>observe, query, reason, and propose</strong> without restriction. '
    'But <strong>sending a message, modifying a record, executing a transaction</strong> '
    '— that requires a human to explicitly approve it.'
    '<br><br>'
    'This is what allows a business to hand off more and more work to the agent over time '
    'without losing control. The approval gate is not a limitation. It is the feature.'
    '</div></div>',
    unsafe_allow_html=True,
)

st.markdown("")

# ── Live Dashboard ───────────────────────────────────────────────────────────

st.markdown("### Live system status")

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
            context = await (await conn.execute("SELECT count(*) as cnt FROM spine_agent.context_entries")).fetchone()
        return orders, customers, products, skills, context

    orders, customers, products, skills, context = run_async(get_stats())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Orders", f"{orders['cnt']:,}")
    c2.metric("Revenue", format_currency(orders['total']))
    c3.metric("Customers", f"{customers['cnt']:,}")
    c4.metric("Active Skills", f"{skills['cnt']}")
    c5.metric("Context Entries", f"{context['cnt']}")

    st.markdown("")

    # Recent activity
    from agent.context_store import search_structured
    recent = run_async(search_structured(limit=5))
    if recent:
        st.markdown("**Recent agent activity**")
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

except Exception as e:
    st.error(f"Database connection error: {e}")
    st.info("Make sure Docker is running: `sudo docker compose up -d`")

st.markdown("")

# ── Implementation details ───────────────────────────────────────────────────

st.markdown("### How it's built")

st.markdown(
    '<div class="card" style="max-width:800px">'
    '<div class="feature-desc" style="max-width:100%;line-height:1.8">'
    '<strong>Spine Object</strong> — A unified Pydantic model that reconstructs a SalesOrder '
    'from 10+ tables across 4 schemas (Sales, Production, Person, Purchasing) '
    'via 3 parameterized SQL queries. One call, complete business context.'
    '<br><br>'
    '<strong>Context Store</strong> — PostgreSQL + pgvector. Every decision, action result, '
    'and state snapshot is stored with a vector embedding for semantic search. '
    'The agent accumulates institutional memory over time.'
    '<br><br>'
    '<strong>Skill Registry</strong> — Skills are registered in the database with specs, '
    'usage stats, and description embeddings. The agent finds the right skill by domain or semantic similarity.'
    '<br><br>'
    '<strong>AutoSkill Loop</strong> — When no skill matches, Claude generates Python code, '
    'a validator checks syntax and class structure in a sandbox, and the new skill is persisted '
    'to the registry. Next time the same need arises, the skill already exists.'
    '<br><br>'
    '<strong>Approval Gate</strong> — Every write action creates a pending approval record in PostgreSQL '
    'with full context (what, why, proposed payload). Approvals expire after 2 hours. '
    'The human approves or rejects. The agent executes or stands down.'
    '</div></div>',
    unsafe_allow_html=True,
)

st.markdown("")

st.markdown("### Tech stack")

t1, t2, t3, t4 = st.columns(4)

with t1:
    st.markdown(
        '<div class="card" style="text-align:center;padding:20px">'
        '<div style="font-size:0.75rem;color:' + COLORS["text_dim"] + ';text-transform:uppercase;letter-spacing:0.06em">LLM</div>'
        '<div style="color:' + COLORS["text"] + ';font-weight:600;margin-top:4px">Claude API</div>'
        '<div style="color:' + COLORS["text_muted"] + ';font-size:0.8rem">Sonnet for routing & planning<br>Opus-capable</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with t2:
    st.markdown(
        '<div class="card" style="text-align:center;padding:20px">'
        '<div style="font-size:0.75rem;color:' + COLORS["text_dim"] + ';text-transform:uppercase;letter-spacing:0.06em">Database</div>'
        '<div style="color:' + COLORS["text"] + ';font-weight:600;margin-top:4px">PostgreSQL 16 + pgvector</div>'
        '<div style="color:' + COLORS["text_muted"] + ';font-size:0.8rem">AdventureWorks OLTP<br>Vector semantic search</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with t3:
    st.markdown(
        '<div class="card" style="text-align:center;padding:20px">'
        '<div style="font-size:0.75rem;color:' + COLORS["text_dim"] + ';text-transform:uppercase;letter-spacing:0.06em">Integrations</div>'
        '<div style="color:' + COLORS["text"] + ';font-weight:600;margin-top:4px">MCP Servers</div>'
        '<div style="color:' + COLORS["text_muted"] + ';font-size:0.8rem">Tiendanube e-commerce<br>Telegram Bot</div>'
        '</div>',
        unsafe_allow_html=True,
    )

with t4:
    st.markdown(
        '<div class="card" style="text-align:center;padding:20px">'
        '<div style="font-size:0.75rem;color:' + COLORS["text_dim"] + ';text-transform:uppercase;letter-spacing:0.06em">Runtime</div>'
        '<div style="color:' + COLORS["text"] + ';font-weight:600;margin-top:4px">Python 3.11+ async</div>'
        '<div style="color:' + COLORS["text_muted"] + ';font-size:0.8rem">Pydantic models<br>Docker Compose</div>'
        '</div>',
        unsafe_allow_html=True,
    )
