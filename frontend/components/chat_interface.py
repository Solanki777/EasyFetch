"""Chat interface component — renders history, handles input, calls backend."""
from __future__ import annotations

import streamlit as st

from frontend.components.result_card import render_result_card
from frontend.utils.api_client import APIClient


def render_chat(client: APIClient) -> None:
    # ── Render conversation history ───────────────────────────────────────────
    for turn in st.session_state.chat_history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
        if turn.get("results"):
            _render_results(turn["results"])

    # ── Handle pending file open from a previous turn ─────────────────────────
    if st.session_state.get("pending_open_file"):
        f = st.session_state.pending_open_file
        link = f.get("web_view_link", "#")
        st.info(f"📂 Opening **{f.get('name', 'file')}** → [Click to open]({link})")
        st.session_state.pending_open_file = None

    # ── Chat input ────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Search your Drive… e.g. 'find Q3 reports from last month'"):
        # Append user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call backend
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching Drive…"):
                try:
                    resp = client.chat(
                        session_id=st.session_state.session_id,
                        message=prompt,
                    )
                except Exception as exc:
                    st.error(f"Backend error: {exc}")
                    return

            reply = resp.get("reply", "Something went wrong.")
            results = resp.get("results", [])
            open_file = resp.get("open_file")

            st.markdown(reply)

            # Show clarification banner
            if resp.get("clarification_needed"):
                st.info("💡 " + (resp.get("clarification_prompt") or "Could you provide more details?"))

            # Show result count badge
            if results:
                st.caption(f"Found **{len(results)}** result{'s' if len(results) != 1 else ''}")
                _render_results(results)

            # Handle open_file action
            if open_file and open_file.get("web_view_link"):
                link = open_file["web_view_link"]
                name = open_file.get("name", "file")
                st.success(f"📂 Opening **{name}** → [Open in Drive]({link})")
                st.session_state.pending_open_file = open_file

        # Update state
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": reply,
            "results": results,
        })
        st.session_state.active_filters = resp.get("active_filters", {})
        st.session_state.last_result_count = resp.get("result_count", 0)


def _render_results(results: list) -> None:
    """Render a list of file results as cards, grouped by folder."""
    if not results:
        return

    # Group by folder for visual organisation
    folders: dict[str, list] = {}
    for r in results:
        folder = r.get("parent_folder_name") or "My Drive"
        folders.setdefault(folder, []).append(r)

    if len(folders) > 1:
        for folder, files in folders.items():
            with st.expander(f"📂 {folder} ({len(files)} file{'s' if len(files)!=1 else ''})", expanded=True):
                for i, result in enumerate(files):
                    render_result_card(result, index=i)
    else:
        for i, result in enumerate(results):
            render_result_card(result, index=i)
