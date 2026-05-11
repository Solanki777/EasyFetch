"""
Drive Assistant — Streamlit frontend entrypoint.

Run with:
  streamlit run frontend/app.py
"""
from __future__ import annotations

import streamlit as st

from frontend.components.active_filters import render_active_filters
from frontend.components.chat_interface import render_chat
from frontend.state.session import init_session_state, reset_session
from frontend.utils.api_client import APIClient

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Drive Assistant",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark background */
.stApp {
    background: linear-gradient(160deg, #020617 0%, #0f172a 60%, #1e1b4b 100%);
    min-height: 100vh;
}

/* Chat input */
.stChatInput > div {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
}

/* Chat messages */
.stChatMessage {
    background: transparent !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b;
}

/* Expander */
[data-testid="stExpander"] {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 8px;
}

/* Spinner */
.stSpinner > div {
    border-top-color: #7dd3fc !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Session init ──────────────────────────────────────────────────────────────
init_session_state()
client = APIClient()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📁 Drive Assistant")
    st.markdown(
        "<p style='color:#64748b;font-size:0.85em;'>"
        "Conversational AI Google Drive search powered by LangGraph + Groq."
        "</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("### 💡 Try asking")
    examples = [
        "Find my Q3 budget reports",
        "Show PDFs from last month",
        "Find spreadsheets in the Finance folder",
        "Newest project proposals",
        "Search inside files for 'revenue'",
        "Open the second result",
    ]
    for ex in examples:
        st.markdown(
            f'<p style="color:#7dd3fc;font-size:0.8em;margin:2px 0;">→ {ex}</p>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Stats
    if st.session_state.last_result_count:
        st.metric("Last search", f"{st.session_state.last_result_count} results")

    turns = len(st.session_state.chat_history) // 2
    st.metric("Conversation turns", turns)

    st.divider()

    # Backend health
    try:
        h = client.health()
        st.success(f"✅ Backend v{h.get('version','?')} · {h.get('session_count',0)} sessions")
    except Exception:
        st.error("❌ Backend unreachable")

    if st.button("🔄 New Conversation", use_container_width=True):
        reset_session()
        st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='color:#f1f5f9;font-weight:700;margin-bottom:4px;'>📁 Drive Assistant</h1>"
    "<p style='color:#64748b;margin-top:0;'>Your conversational Google Drive search companion</p>",
    unsafe_allow_html=True,
)

render_active_filters(st.session_state.active_filters)
render_chat(client)
