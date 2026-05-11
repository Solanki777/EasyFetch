"""
Result card component — renders a single DriveFile as a styled HTML card.
Uses st.markdown with unsafe_allow_html for rich card layout.
"""
from __future__ import annotations

import streamlit as st
from datetime import datetime
from frontend.utils.mime_icons import get_mime_icon


def render_result_card(result: dict, index: int = 0) -> None:
    icon      = get_mime_icon(result.get("mime_type", ""))
    name      = result.get("name", "Unknown")
    link      = result.get("web_view_link") or "#"
    folder    = result.get("parent_folder_name") or "My Drive"
    score     = result.get("relevance_score", 0.0)
    reasons   = result.get("match_reason") or []
    sim_group = result.get("similarity_group")
    modified  = _fmt_date(result.get("modified_time", ""))
    size_str  = _fmt_size(result.get("size_bytes"))

    # Score colour
    if score >= 70:
        score_colour = "#22c55e"   # green
    elif score >= 40:
        score_colour = "#f59e0b"   # amber
    else:
        score_colour = "#94a3b8"   # slate

    reasons_html = ""
    if reasons:
        tags = "".join(
            f'<span style="background:#1e3a5f;color:#7dd3fc;border-radius:4px;'
            f'padding:2px 6px;font-size:0.7em;margin-right:4px;">{r}</span>'
            for r in reasons
        )
        reasons_html = f'<div style="margin-top:6px;">{tags}</div>'

    sim_badge = ""
    if sim_group:
        sim_badge = (
            '<span style="font-size:0.65em;background:#2d1b69;color:#c4b5fd;'
            'border-radius:4px;padding:2px 6px;margin-left:6px;">similar group</span>'
        )

    size_html = f'<span style="margin-left:8px;">· {size_str}</span>' if size_str else ""

    card_html = f"""
<div style="
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid #334155;
    border-left: 3px solid {score_colour};
    border-radius: 10px;
    padding: 14px 18px;
    margin: 8px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    transition: transform 0.15s;
">
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div style="flex:1; min-width:0;">
            <span style="font-size:1.15em; font-weight:600; color:#f1f5f9;">
                {icon}&nbsp;
                <a href="{link}" target="_blank"
                   style="color:#7dd3fc; text-decoration:none;">{name}</a>
            </span>
            {sim_badge}
        </div>
        <div style="
            background: {score_colour}22;
            border: 1px solid {score_colour};
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.75em;
            font-weight: 700;
            color: {score_colour};
            white-space: nowrap;
            margin-left: 10px;
        ">{score:.0f} pts</div>
    </div>
    <div style="font-size:0.8em; color:#94a3b8; margin-top:6px;">
        📂 {folder}&nbsp;&nbsp;🕒 {modified}{size_html}
    </div>
    {reasons_html}
</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_date(dt_str: str) -> str:
    if not dt_str:
        return "unknown"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return dt_str


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
