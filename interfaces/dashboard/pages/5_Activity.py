"""Activity — agent loop viewer, execution history, and approval queue."""

import json
import streamlit as st
from interfaces.dashboard.helpers import inject_css, run_async, format_currency, COLORS

st.set_page_config(page_title="SpineAgent — Activity", page_icon="📊", layout="wide")
inject_css()

st.markdown("### Activity")
st.caption("See what the agent is doing: routing decisions, skill executions, and pending approvals.")

# ── Pending Approvals (notification style at the top) ────────────────────────
from agent.approval_gate import list_pending, approve, reject

pending = run_async(list_pending())

if pending:
    st.markdown(
        f'<div class="card card-accent-amber" style="padding:16px 24px">'
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<div style="font-size:1.5rem">&#9888;</div>'
        f'<div>'
        f'<div style="color:{COLORS["warning"]};font-weight:700;font-size:0.95rem">'
        f'{len(pending)} pending approval{"s" if len(pending) > 1 else ""}</div>'
        f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem">'
        f'The agent proposed write actions that need your review.</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("")

    for appr in pending:
        payload = appr.get("action_payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                pass
        ctx = appr.get("context", {})
        if isinstance(ctx, str):
            try:
                ctx = json.loads(ctx)
            except json.JSONDecodeError:
                pass

        with st.container():
            st.markdown(
                f'<div class="card card-accent-red" style="padding:16px 20px">'
                f'<div style="display:flex;justify-content:space-between;align-items:start">'
                f'<div>'
                f'<span style="color:{COLORS["text"]};font-weight:600">#{appr["id"]} {appr["action_type"]}</span>'
                f'<br><span style="color:{COLORS["text_dim"]};font-size:0.8rem">{appr["spine_object_id"]}</span>'
                f'</div>'
                f'<span style="color:{COLORS["text_dim"]};font-size:0.75rem">{str(appr["created_at"])[:19]}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            with st.expander(f"View details for approval #{appr['id']}"):
                st.markdown("**Proposed action:**")
                st.json(payload)
                if ctx:
                    st.markdown("**Context:**")
                    st.json(ctx)

                col_approve, col_reject, col_space = st.columns([1, 1, 3])
                if col_approve.button("Approve", key=f"approve_{appr['id']}", type="primary"):
                    run_async(approve(appr["id"]))
                    st.success(f"Approval #{appr['id']} approved.")
                    st.rerun()
                if col_reject.button("Reject", key=f"reject_{appr['id']}"):
                    run_async(reject(appr["id"]))
                    st.warning(f"Approval #{appr['id']} rejected.")
                    st.rerun()

    st.markdown("")
else:
    st.markdown(
        f'<div class="card" style="padding:12px 20px">'
        f'<span style="color:{COLORS["success"]};font-weight:600;font-size:0.85rem">No pending approvals</span>'
        f' <span style="color:{COLORS["text_muted"]};font-size:0.8rem">— all clear.</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("")

# ── Execution History (from context store) ───────────────────────────────────
st.markdown(
    f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;'
    f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px">Execution history</div>',
    unsafe_allow_html=True,
)

from agent.context_store import search_structured
entries = run_async(search_structured(limit=30))

if not entries:
    st.caption("No activity yet. Use the Chat page to interact with the agent.")
else:
    # Group by entry type for stats
    type_counts = {}
    for e in entries:
        t = e["entry_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    type_cols = st.columns(len(type_counts) + 1)
    type_cols[0].metric("Total Entries", len(entries))
    for i, (etype, count) in enumerate(sorted(type_counts.items())):
        type_cols[i + 1].metric(etype.replace("_", " ").title(), count)

    st.markdown("")

    # Filters
    filter_cols = st.columns([2, 2, 1])
    filter_type = filter_cols[0].selectbox(
        "Filter by type", ["All"] + sorted(type_counts.keys()), label_visibility="collapsed"
    )
    filter_source = filter_cols[1].selectbox(
        "Filter by source", ["All", "agent", "human", "system"], label_visibility="collapsed"
    )

    filtered = entries
    if filter_type != "All":
        filtered = [e for e in filtered if e["entry_type"] == filter_type]
    if filter_source != "All":
        filtered = [e for e in filtered if e.get("source") == filter_source]

    st.markdown("")

    # Timeline
    for entry in filtered[:20]:
        content = entry.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {"raw": content}

        # Pick the best summary
        if isinstance(content, dict):
            summary = (
                content.get("user_message")
                or content.get("message")
                or content.get("result_summary")
                or content.get("action")
                or str(content)[:100]
            )
        else:
            summary = str(content)[:100]

        # Color by type
        type_color = {
            "action_result": COLORS["primary"],
            "state_snapshot": COLORS["success"],
            "decision": COLORS["warning"],
            "pattern": "#a78bfa",
            "rule": COLORS["text_dim"],
        }.get(entry["entry_type"], COLORS["text_dim"])

        source_label = entry.get("source", "system")

        st.markdown(
            f'<div class="card" style="padding:12px 20px;margin-bottom:6px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<div>'
            f'<span style="color:{type_color};font-weight:600;font-size:0.75rem;'
            f'background:{type_color}22;padding:2px 8px;border-radius:8px">{entry["entry_type"]}</span>'
            f' <span style="color:{COLORS["text_dim"]};font-size:0.7rem;'
            f'background:{COLORS["text_dim"]}22;padding:2px 6px;border-radius:6px">{source_label}</span>'
            f' <span style="color:{COLORS["text_muted"]};font-size:0.8rem;margin-left:8px">'
            f'{entry["spine_object_id"]}</span>'
            f'</div>'
            f'<span style="color:{COLORS["text_dim"]};font-size:0.7rem">{str(entry["created_at"])[:19]}</span>'
            f'</div>'
            f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem;margin-top:6px">{summary}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("")

# ── Approval History ─────────────────────────────────────────────────────────
st.markdown(
    f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;'
    f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px">Approval history</div>',
    unsafe_allow_html=True,
)

from agent.db import get_connection

async def get_approval_history():
    async with await get_connection() as conn:
        return await (await conn.execute(
            """SELECT id, spine_object_id, action_type, status, requested_by,
                      approved_by, decision_note, created_at, decided_at
               FROM spine_agent.pending_approvals
               ORDER BY created_at DESC LIMIT 20"""
        )).fetchall()

approval_history = run_async(get_approval_history())

if approval_history:
    for a in approval_history:
        status_color = {
            "approved": COLORS["success"],
            "rejected": COLORS["danger"],
            "pending": COLORS["warning"],
            "expired": COLORS["text_dim"],
        }.get(a["status"], COLORS["text_dim"])

        st.markdown(
            f'<div class="card" style="padding:10px 20px;margin-bottom:6px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<div>'
            f'<span style="color:{COLORS["text"]};font-weight:600;font-size:0.85rem">#{a["id"]}</span>'
            f' <span style="color:{COLORS["text_muted"]};font-size:0.8rem">{a["action_type"]}</span>'
            f' <span style="color:{status_color};font-size:0.7rem;font-weight:600;'
            f'background:{status_color}22;padding:2px 8px;border-radius:8px">{a["status"]}</span>'
            f'</div>'
            f'<span style="color:{COLORS["text_dim"]};font-size:0.7rem">{str(a["created_at"])[:19]}</span>'
            f'</div>'
            f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;margin-top:4px">'
            f'{a["spine_object_id"]}'
            f'{" — " + a["decision_note"] if a.get("decision_note") else ""}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.caption("No approval history yet.")
