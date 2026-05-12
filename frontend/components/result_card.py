
"""
Result card component using native Streamlit UI.
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from frontend.utils.mime_icons import get_mime_icon


def render_result_card(
    result: dict,
    index: int = 0
) -> None:

    icon = get_mime_icon(
        result.get("mime_type", "")
    )

    name = result.get(
        "name",
        "Unknown"
    )

    link = result.get(
        "web_view_link"
    ) or "#"

    folder = result.get(
        "parent_folder_name"
    ) or "My Drive"

    score = result.get(
        "relevance_score",
        0
    )

    modified = _fmt_date(
        result.get("modified_time")
    )

    size = _fmt_size(
        result.get("size_bytes")
    )

    reasons = result.get(
        "match_reason",
        []
    )

    sim_group = result.get(
        "similarity_group"
    )

    with st.container(border=True):

        top_cols = st.columns([8, 2])

        with top_cols[0]:

            st.markdown(
                f"### {icon} [{name}]({link})"
            )

            meta = f"📂 {folder} • 🕒 {modified}"

            if size:
                meta += f" • 📦 {size}"

            st.caption(meta)

        with top_cols[1]:

            st.metric(
                "Score",
                f"{int(score)}"
            )

        if sim_group:
            st.caption(
                f"🔗 Similar Group: {sim_group}"
            )

        if reasons:

            badges = " ".join(
                [
                    f"`{reason}`"
                    for reason in reasons
                ]
            )

            st.markdown(badges)

        st.divider()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_date(dt_str: str) -> str:

    if not dt_str:
        return "unknown"

    try:

        dt = datetime.fromisoformat(
            dt_str.replace("Z", "+00:00")
        )

        return dt.strftime(
            "%b %d, %Y"
        )

    except Exception:
        return str(dt_str)


def _fmt_size(size_bytes) -> str:

    if not size_bytes:
        return ""

    try:

        b = int(size_bytes)

        if b < 1024:
            return f"{b} B"

        elif b < 1024 ** 2:
            return f"{b / 1024:.1f} KB"

        elif b < 1024 ** 3:
            return f"{b / 1024**2:.1f} MB"

        return f"{b / 1024**3:.1f} GB"

    except Exception:
        return ""
