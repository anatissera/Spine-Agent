"""Chat — interactive agent conversation."""

import streamlit as st
from interfaces.dashboard.helpers import inject_css, run_async, COLORS

st.set_page_config(page_title="SpineAgent — Chat", page_icon="💬", layout="wide")
inject_css()

st.markdown("### Chat with SpineAgent")
st.caption("Ask about orders, customers, inventory — or request actions.")

# ── Session state ────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    from agent.core import SpineAgent
    st.session_state.agent = SpineAgent()

agent = st.session_state.agent

# ── Chat history ─────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Suggestion cards (if empty) ──────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("")
    st.markdown(f'<p style="color:{COLORS["text_muted"]};font-size:0.85rem">Try one of these to get started:</p>', unsafe_allow_html=True)

    suggestions = [
        ("Order Status", "What is the status of order 43659?"),
        ("Customer Lookup", "Who is the customer for order 46616?"),
        ("Order Items", "List all items in order 51131"),
        ("Check Inventory", "Check inventory for order 43661"),
        ("Notify Customer", "Notify the customer of order 43659 that their order shipped"),
        ("Profit Margin", "What is the profit margin for order 43659?"),
    ]

    cols = st.columns(3)
    for i, (label, prompt) in enumerate(suggestions):
        with cols[i % 3]:
            if st.button(label, key=f"sug_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.rerun()

# ── Chat input ───────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about an order, customer, or request an action..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(""):
            try:
                response = run_async(agent.handle_message(prompt))
            except Exception as e:
                response = f"Error: {e}"
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

# ── Sidebar controls ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Conversation")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        from agent.core import SpineAgent
        st.session_state.agent = SpineAgent()
        st.rerun()

    st.markdown("")
    st.markdown("### Approval Gate")
    st.caption("Use these when the agent proposes a write action.")
    c1, c2 = st.columns(2)
    if c1.button("Approve", use_container_width=True, type="primary"):
        st.session_state.messages.append({"role": "user", "content": "approve"})
        st.rerun()
    if c2.button("Reject", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "reject"})
        st.rerun()
