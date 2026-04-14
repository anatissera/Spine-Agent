"""Monitor page — real-time anomaly detection and alerts."""

import streamlit as st
from interfaces.dashboard.helpers import run_async, format_currency, ALERT_ICONS

st.set_page_config(page_title="SpineAgent — Monitor", page_icon="👁️", layout="wide")

st.title("👁️ Monitor")
st.markdown("Real-time anomaly detection across all orders.")

# ── Run monitor ──────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
limit = col1.slider("Max alerts to scan", 10, 100, 30)
run_btn = col2.button("🔄 Run Monitor", use_container_width=True)

if run_btn or "monitor_alerts" not in st.session_state:
    from monitor.rules import detect_stale_orders, detect_overdue_orders

    with st.spinner("Scanning for anomalies..."):
        stale = run_async(detect_stale_orders(limit=limit))
        overdue = run_async(detect_overdue_orders(limit=limit))

    st.session_state.monitor_alerts = {"stale": stale, "overdue": overdue}

alerts = st.session_state.get("monitor_alerts", {"stale": [], "overdue": []})
stale = alerts["stale"]
overdue = alerts["overdue"]
total = len(stale) + len(overdue)

# ── KPIs ─────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Alerts", total)
k2.metric("Stale Orders", len(stale))
k3.metric("Overdue Orders", len(overdue))
high_count = sum(1 for a in stale + overdue if a.get("level") == "HIGH")
k4.metric("High Severity", high_count)

st.divider()

# ── Stale Orders ─────────────────────────────────────────────────────────────
st.markdown("### ⏰ Stale Orders")
st.markdown("Orders that have been in their current status longer than expected.")

if stale:
    stale_data = []
    for a in stale:
        stale_data.append({
            "": ALERT_ICONS.get(a["level"], "⚠️"),
            "Order": f"#{a['order_id']}",
            "Status": a["status_label"],
            "Hours Stale": f"{a['hours_stale']:.0f}h",
            "Threshold": f"{a['threshold_hours']}h",
            "Customer": a["customer_name"],
            "Total": format_currency(a["total_due"]),
        })
    st.dataframe(stale_data, use_container_width=True, hide_index=True)
else:
    st.success("No stale orders detected")

st.divider()

# ── Overdue Orders ───────────────────────────────────────────────────────────
st.markdown("### ⚠️ Overdue Orders")
st.markdown("Orders past their due date that haven't shipped.")

if overdue:
    overdue_data = []
    for a in overdue:
        overdue_data.append({
            "": "🔴",
            "Order": f"#{a['order_id']}",
            "Days Overdue": a["days_overdue"],
            "Customer": a["customer_name"],
            "Total": format_currency(a["total_due"]),
        })
    st.dataframe(overdue_data, use_container_width=True, hide_index=True)
else:
    st.success("No overdue orders detected")

# ── Alert detail expander ────────────────────────────────────────────────────
if stale:
    st.divider()
    st.markdown("### Alert Details")
    for a in stale[:5]:
        with st.expander(f"{ALERT_ICONS.get(a['level'], '⚠️')} Order #{a['order_id']} — {a['status_label']} for {a['hours_stale']:.0f}h"):
            col_a, col_b = st.columns(2)
            col_a.markdown(f"""
            - **Customer:** {a['customer_name']}
            - **Total:** {format_currency(a['total_due'])}
            - **Order Date:** {a.get('order_date', '—')}
            """)
            col_b.markdown(f"""
            - **Due Date:** {a.get('due_date', '—')}
            - **Status:** {a['status_label']}
            - **Hours Stale:** {a['hours_stale']:.1f}h (threshold: {a['threshold_hours']}h)
            """)
            st.page_link("pages/2_Spine_Explorer.py", label=f"View Order #{a['order_id']} in Spine Explorer →")
