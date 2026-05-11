"""st.session_state initialisation and accessors."""
from __future__ import annotations

import uuid
import streamlit as st


def init_session_state() -> None:
    """Idempotent — safe to call on every Streamlit rerun."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "chat_history" not in st.session_state:
        # Each entry: {"role": "user"|"assistant", "content": str, "results": list}
        st.session_state.chat_history = []

    if "active_filters" not in st.session_state:
        st.session_state.active_filters = {}

    if "last_result_count" not in st.session_state:
        st.session_state.last_result_count = 0

    if "pending_open_file" not in st.session_state:
        st.session_state.pending_open_file = None


def reset_session() -> None:
    """Clear conversation and start fresh (new session_id)."""
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.active_filters = {}
    st.session_state.last_result_count = 0
    st.session_state.pending_open_file = None
