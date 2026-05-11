"""Active filters bar — shows current search constraints as dismissible chips."""
from __future__ import annotations

import streamlit as st


FILTER_LABELS: dict[str, str] = {
    "filename_query":   "🔍 Name",
    "file_extensions":  "📄 Type",
    "mime_types":       "📄 MIME",
    "folder_name":      "📂 Folder",
    "sort_by":          "↕️ Sort",
    "date_filter":      "📅 Date",
    "search_in_content": "📝 Content",
    "result_limit":     "🔢 Limit",
}

_SKIP = {"is_followup", "followup_action", "raw_query",
         "needs_clarification", "clarification_question",
         "folder_id", "open_file_index"}


def render_active_filters(filters: dict) -> None:
    """Render active filter chips. Chip click sends a removal follow-up."""
    if not filters:
        return

    visible = {
        k: v for k, v in filters.items()
        if k not in _SKIP and v not in (None, [], False, "relevance", 10)
    }
    if not visible:
        return

    st.markdown(
        '<p style="font-size:0.78em;color:#64748b;margin-bottom:4px;">'
        '🎯 Active filters</p>',
        unsafe_allow_html=True,
    )

    chips_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">'
    for key, val in visible.items():
        label = FILTER_LABELS.get(key, key.replace("_", " ").title())
        display = _display_value(key, val)
        chips_html += (
            f'<span style="'
            f'background:#1e293b;border:1px solid #334155;'
            f'border-radius:20px;padding:3px 10px;'
            f'font-size:0.75em;color:#94a3b8;white-space:nowrap;">'
            f'{label}: <strong style="color:#e2e8f0;">{display}</strong>'
            f'</span>'
        )
    chips_html += "</div>"
    st.markdown(chips_html, unsafe_allow_html=True)


def _display_value(key: str, val) -> str:
    if isinstance(val, list):
        return ", ".join(str(v).upper() for v in val[:3])
    if isinstance(val, dict):
        # date_filter
        rel = val.get("relative")
        if rel:
            return rel.replace("_", " ")
        after = val.get("after", "")[:10]
        before = val.get("before", "")[:10]
        return f"{after} → {before}" if after or before else "custom"
    if isinstance(val, bool):
        return "on" if val else "off"
    return str(val)
