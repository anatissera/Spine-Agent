"""Spine Explorer — browse and view orders with the full unified spine."""

import streamlit as st
import plotly.graph_objects as go
from interfaces.dashboard.helpers import run_async, format_currency, status_badge

st.set_page_config(page_title="SpineAgent — Spine Explorer", page_icon="🔍", layout="wide")

st.title("🔍 Spine Explorer")
st.markdown("View the unified representation of any sales order across all domains.")

# ── Order lookup ─────────────────────────────────────────────────────────────
col_input, col_btn = st.columns([3, 1])
order_id = col_input.number_input("Order ID", min_value=1, value=43659, step=1)
lookup = col_btn.button("🔍 Load Order", use_container_width=True)

if lookup or "spine_order" in st.session_state:
    from agent.spine import get_spine

    with st.spinner("Loading spine..."):
        spine = run_async(get_spine(int(order_id)))

    if spine is None:
        st.error(f"Order {order_id} not found")
    else:
        st.session_state.spine_order = spine

        # ── Header ───────────────────────────────────────────────────────
        st.markdown(f"## Order #{spine.sales_order_id}")
        st.markdown(status_badge(spine.status), unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Due", format_currency(spine.total_due))
        col2.metric("Items", len(spine.items))
        col3.metric("Order Date", str(spine.order_date)[:10])
        col4.metric("Ship Date", str(spine.ship_date)[:10] if spine.ship_date else "—")

        st.divider()

        # ── Two-column layout: Customer + Addresses ──────────────────────
        left, right = st.columns(2)

        with left:
            st.markdown("### 👤 Customer")
            c = spine.customer
            st.markdown(f"""
            | Field | Value |
            |-------|-------|
            | **Name** | {c.first_name or ''} {c.last_name or ''} |
            | **Email** | {c.email or '—'} |
            | **Phone** | {c.phone or '—'} |
            | **Customer ID** | {c.customer_id} |
            | **Store** | {c.store_name or '—'} |
            """)

        with right:
            st.markdown("### 📍 Addresses")
            addr_col1, addr_col2 = st.columns(2)
            with addr_col1:
                st.markdown("**Ship To:**")
                a = spine.ship_to
                st.markdown(f"{a.address_line1}  \n{a.city}, {a.state_province} {a.postal_code}")
            with addr_col2:
                st.markdown("**Bill To:**")
                a = spine.bill_to
                st.markdown(f"{a.address_line1}  \n{a.city}, {a.state_province} {a.postal_code}")

        st.divider()

        # ── Financials breakdown ─────────────────────────────────────────
        st.markdown("### 💰 Financials")
        fin_cols = st.columns(4)
        fin_cols[0].metric("Subtotal", format_currency(spine.subtotal))
        fin_cols[1].metric("Tax", format_currency(spine.tax))
        fin_cols[2].metric("Freight", format_currency(spine.freight))
        fin_cols[3].metric("Total", format_currency(spine.total_due))

        st.divider()

        # ── Line items table ─────────────────────────────────────────────
        st.markdown("### 📦 Line Items")
        items_data = []
        for item in spine.items:
            margin = float(item.unit_price - item.standard_cost) / float(item.unit_price) * 100 if float(item.unit_price) > 0 else 0
            items_data.append({
                "Product": item.product_name,
                "SKU": item.product_number,
                "Color": item.color or "—",
                "Qty": item.order_qty,
                "Unit Price": format_currency(item.unit_price),
                "Line Total": format_currency(item.line_total),
                "Margin": f"{margin:.1f}%",
            })
        st.dataframe(items_data, use_container_width=True, hide_index=True)

        # ── Inventory chart ──────────────────────────────────────────────
        if spine.inventory:
            st.divider()
            st.markdown("### 📊 Product Inventory")
            inv_names = [inv.product_name[:30] for inv in spine.inventory]
            inv_qtys = [inv.total_quantity for inv in spine.inventory]

            fig = go.Figure(data=[
                go.Bar(
                    x=inv_names,
                    y=inv_qtys,
                    marker_color=["#66BB6A" if q > 100 else "#FFA726" if q > 10 else "#EF5350" for q in inv_qtys],
                )
            ])
            fig.update_layout(
                title="Stock Levels for Products in This Order",
                xaxis_title="Product",
                yaxis_title="Total Quantity",
                height=400,
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Context history ──────────────────────────────────────────────
        st.divider()
        st.markdown("### 📝 Context History")
        from agent.context_store import get_entries_for_spine
        entries = run_async(get_entries_for_spine(f"SalesOrder:{spine.sales_order_id}"))
        if entries:
            for e in entries[:10]:
                with st.expander(f"[{e['entry_type']}] {str(e['created_at'])[:19]} — {e['source']}"):
                    st.json(e.get("content", {}))
        else:
            st.info("No context history for this order yet. Interact via Chat to build context.")
