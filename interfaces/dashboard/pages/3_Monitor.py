"""Monitor — real-time anomaly detection and alerts."""

import streamlit as st
from interfaces.dashboard.helpers import inject_css, run_async, format_currency, COLORS

st.set_page_config(page_title="SpineAgent — Monitor", page_icon="👁️", layout="wide")
inject_css()

st.markdown("### Monitor")
st.caption("Real-time anomaly detection across all orders. Runs automatically or on demand.")

# ── Controls ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
limit = col1.slider("Scan depth", 10, 100, 30, label_visibility="collapsed")
run_btn = col2.button("Run Scan", use_container_width=True, type="primary")

if run_btn or "monitor_ran" not in st.session_state:
    from monitor.rules import detect_stale_orders, detect_overdue_orders
    with st.spinner(""):
        stale = run_async(detect_stale_orders(limit=limit))
        overdue = run_async(detect_overdue_orders(limit=limit))
    st.session_state.monitor_stale = stale
    st.session_state.monitor_overdue = overdue
    st.session_state.monitor_ran = True

stale = st.session_state.get("monitor_stale", [])
overdue = st.session_state.get("monitor_overdue", [])
total = len(stale) + len(overdue)
high = sum(1 for a in stale + overdue if a.get("level") == "HIGH")

# ── KPIs ─────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Alerts", total)
k2.metric("Stale Orders", len(stale))
k3.metric("Overdue", len(overdue))
k4.metric("High Severity", high)

st.divider()

# ── Stale Orders ─────────────────────────────────────────────────────────────
st.markdown("**Stale Orders**")
st.caption("Orders in their current status longer than expected thresholds.")

if stale:
    for a in stale[:10]:
        level_color = COLORS["danger"] if a["level"] == "HIGH" else COLORS["warning"]
        accent = "card-accent-red" if a["level"] == "HIGH" else "card-accent-amber"
        st.markdown(
            f'<div class="card {accent}" style="padding:14px 20px;margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<div>'
            f'<span style="color:{COLORS["text"]};font-weight:600">Order #{a["order_id"]}</span>'
            f' <span style="color:{level_color};font-size:0.75rem;font-weight:600;'
            f'background:{level_color}22;padding:2px 8px;border-radius:10px">{a["level"]}</span>'
            f'</div>'
            f'<span style="color:{COLORS["text_dim"]};font-size:0.8rem">{a["hours_stale"]:.0f}h stale (threshold: {a["threshold_hours"]}h)</span>'
            f'</div>'
            f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem;margin-top:4px">'
            f'{a["status_label"]} — {a["customer_name"]} — {format_currency(a["total_due"])}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.success("No stale orders detected.")

st.divider()

# ── Overdue ──────────────────────────────────────────────────────────────────
st.markdown("**Overdue Orders**")
st.caption("Orders past due date that haven't shipped.")

if overdue:
    for a in overdue[:10]:
        st.markdown(
            f'<div class="card card-accent-red" style="padding:14px 20px;margin-bottom:8px">'
            f'<span style="color:{COLORS["text"]};font-weight:600">Order #{a["order_id"]}</span>'
            f' <span style="color:{COLORS["danger"]};font-size:0.75rem;font-weight:600;'
            f'background:{COLORS["danger_muted"]};padding:2px 8px;border-radius:10px">{a["days_overdue"]} days overdue</span>'
            f'<div style="color:{COLORS["text_muted"]};font-size:0.8rem;margin-top:4px">'
            f'{a["customer_name"]} — {format_currency(a["total_due"])}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.success("No overdue orders detected.")
