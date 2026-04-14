"""Spine Explorer — unified order viewer across all domains."""

import streamlit as st
import plotly.graph_objects as go
from interfaces.dashboard.helpers import inject_css, run_async, format_currency, status_badge_html, COLORS

st.set_page_config(page_title="SpineAgent — Spine Explorer", page_icon="🔍", layout="wide")
inject_css()

st.markdown("### Spine Explorer")
st.caption("Unified representation of a SalesOrder across Sales, Production, Person, and Purchasing domains.")

# ── Order lookup ─────────────────────────────────────────────────────────────
col_input, col_btn = st.columns([4, 1])
order_id = col_input.number_input("Order ID", min_value=1, value=43659, step=1, label_visibility="collapsed")
lookup = col_btn.button("Load Order", use_container_width=True, type="primary")

if lookup or "spine_loaded" in st.session_state:
    from agent.spine import get_spine

    with st.spinner(""):
        spine = run_async(get_spine(int(order_id)))

    if spine is None:
        st.error(f"Order {order_id} not found")
        st.stop()

    st.session_state.spine_loaded = True

    # ── Header ───────────────────────────────────────────────────────
    st.markdown(f"## Order #{spine.sales_order_id}")
    st.markdown(status_badge_html(spine.status), unsafe_allow_html=True)
    st.markdown("")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Due", format_currency(spine.total_due))
    c2.metric("Line Items", len(spine.items))
    c3.metric("Order Date", str(spine.order_date)[:10])
    c4.metric("Ship Date", str(spine.ship_date)[:10] if spine.ship_date else "Pending")

    st.divider()

    # ── Customer + Addresses ─────────────────────────────────────────
    left, right = st.columns(2)

    with left:
        c = spine.customer
        st.markdown(
            f'<div class="card card-accent-blue">'
            f'<div class="feature-title">Customer</div>'
            f'<table style="width:100%;color:{COLORS["text_muted"]};font-size:0.85rem">'
            f'<tr><td style="padding:4px 0;color:{COLORS["text_dim"]}">Name</td><td style="color:{COLORS["text"]};font-weight:500">{c.first_name or ""} {c.last_name or ""}</td></tr>'
            f'<tr><td style="padding:4px 0;color:{COLORS["text_dim"]}">Email</td><td>{c.email or "—"}</td></tr>'
            f'<tr><td style="padding:4px 0;color:{COLORS["text_dim"]}">Phone</td><td>{c.phone or "—"}</td></tr>'
            f'<tr><td style="padding:4px 0;color:{COLORS["text_dim"]}">Store</td><td>{c.store_name or "—"}</td></tr>'
            f'<tr><td style="padding:4px 0;color:{COLORS["text_dim"]}">ID</td><td>#{c.customer_id}</td></tr>'
            f'</table></div>',
            unsafe_allow_html=True,
        )

    with right:
        ship = spine.ship_to
        bill = spine.bill_to
        st.markdown(
            f'<div class="card card-accent-green">'
            f'<div class="feature-title">Addresses</div>'
            f'<div style="display:flex;gap:24px">'
            f'<div style="flex:1">'
            f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">Ship To</div>'
            f'<div style="color:{COLORS["text"]};font-size:0.85rem">{ship.address_line1}<br>{ship.city}, {ship.state_province} {ship.postal_code}</div>'
            f'</div>'
            f'<div style="flex:1">'
            f'<div style="color:{COLORS["text_dim"]};font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">Bill To</div>'
            f'<div style="color:{COLORS["text"]};font-size:0.85rem">{bill.address_line1}<br>{bill.city}, {bill.state_province} {bill.postal_code}</div>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Financials ───────────────────────────────────────────────────
    st.markdown("**Financials**")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Subtotal", format_currency(spine.subtotal))
    f2.metric("Tax", format_currency(spine.tax))
    f3.metric("Freight", format_currency(spine.freight))
    f4.metric("Total", format_currency(spine.total_due))

    st.divider()

    # ── Line items ───────────────────────────────────────────────────
    st.markdown("**Line Items**")
    items_data = []
    for item in spine.items:
        margin = (
            float(item.unit_price - item.standard_cost) / float(item.unit_price) * 100
            if float(item.unit_price) > 0 else 0
        )
        items_data.append({
            "Product": item.product_name,
            "SKU": item.product_number,
            "Color": item.color or "—",
            "Qty": item.order_qty,
            "Unit Price": format_currency(item.unit_price),
            "Total": format_currency(item.line_total),
            "Margin": f"{margin:.1f}%",
        })
    st.dataframe(items_data, use_container_width=True, hide_index=True)

    # ── Inventory chart ──────────────────────────────────────────────
    if spine.inventory:
        st.divider()
        st.markdown("**Product Inventory**")

        names = [inv.product_name[:25] for inv in spine.inventory]
        qtys = [inv.total_quantity for inv in spine.inventory]
        bar_colors = [
            COLORS["success"] if q > 100 else COLORS["warning"] if q > 10 else COLORS["danger"]
            for q in qtys
        ]

        fig = go.Figure(data=[go.Bar(x=names, y=qtys, marker_color=bar_colors)])
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
            yaxis=dict(title="Quantity", gridcolor="#1e293b"),
            font=dict(family="Plus Jakarta Sans"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Context history ──────────────────────────────────────────────
    st.divider()
    st.markdown("**Context History**")
    from agent.context_store import get_entries_for_spine
    entries = run_async(get_entries_for_spine(f"SalesOrder:{spine.sales_order_id}"))
    if entries:
        for e in entries[:8]:
            with st.expander(f"{e['entry_type']} — {str(e['created_at'])[:19]}"):
                st.json(e.get("content", {}))
    else:
        st.caption("No context history yet. Interact via Chat to build context.")
