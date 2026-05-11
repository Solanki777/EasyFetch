"""LangGraph agent state definition."""
from __future__ import annotations

from typing import List, Optional
from typing_extensions import TypedDict

from backend.schemas.drive import DriveFile
from backend.schemas.intent import SearchIntent
from backend.schemas.session import SessionState


class AgentState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────────────────────
    user_message: str
    session: SessionState

    # ── Populated by nodes ────────────────────────────────────────────────────
    intent: Optional[SearchIntent]
    raw_drive_results: Optional[List[DriveFile]]
    ranked_results: Optional[List[DriveFile]]
    grouped_results: Optional[dict]

    # ── Output ────────────────────────────────────────────────────────────────
    reply: Optional[str]
    results: Optional[List[dict]]
    clarification_needed: bool
    clarification_prompt: Optional[str]
    open_file: Optional[dict]
    error: Optional[str]
