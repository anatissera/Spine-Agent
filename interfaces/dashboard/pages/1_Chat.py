"""Chat page — interactive agent conversation with Assist + Act modes."""

import streamlit as st
from interfaces.dashboard.helpers import run_async

st.set_page_config(page_title="SpineAgent — Chat", page_icon="💬", layout="wide")

st.title("💬 Agent Chat")
st.markdown("Ask questions about orders, customers, and inventory — or request actions.")

# ── Session state ────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    from agent.core import SpineAgent
    st.session_state.agent = SpineAgent()

agent = st.session_state.agent

# ── Display chat history ─────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🦴"):
        st.markdown(msg["content"])

# ── Suggested prompts (only show if no messages yet) ─────────────────────────
if not st.session_state.messages:
    st.markdown("#### Try these:")
    cols = st.columns(2)
    suggestions = [
        ("📦 Order Status", "What is the status of order 43659?"),
        ("👤 Customer Info", "Who is the customer for order 46616?"),
        ("📋 Order Items", "What items are in order 51131?"),
        ("📊 Inventory", "Check inventory for order 43661"),
        ("⚡ Notify Customer", "Notify the customer of order 43659 that their order shipped"),
        ("🧠 AutoSkill", "What is the profit margin for order 43659?"),
    ]
    for i, (label, prompt) in enumerate(suggestions):
        col = cols[i % 2]
        if col.button(label, key=f"sug_{i}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

# ── Chat input ───────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about an order, customer, or inventory..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🦴"):
        with st.spinner("Thinking..."):
            try:
                response = run_async(agent.handle_message(prompt))
            except Exception as e:
                response = f"Error: {e}"
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

# ── Sidebar: conversation controls ──────────────────────────────────────────
with st.sidebar:
    st.markdown("### Conversation")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        from agent.core import SpineAgent
        st.session_state.agent = SpineAgent()
        st.rerun()

    st.divider()
    st.markdown("### Quick Actions")
    if st.button("✅ Approve", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "approve"})
        st.rerun()
    if st.button("❌ Reject", use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": "reject"})
        st.rerun()
