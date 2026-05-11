"""
POST /api/v1/chat — main conversational search endpoint.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.agent.graph import build_graph
from backend.dependencies import get_session_manager
from backend.schemas.api import ChatRequest, ChatResponse, FileResult
from backend.session.manager import SessionManager

logger = logging.getLogger(__name__)
router = APIRouter()

# Compile the graph once at module load
_graph = build_graph()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
) -> ChatResponse:
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        session = session_manager.get_or_create(payload.session_id)

        result = await _graph.ainvoke({
            "user_message": payload.message,
            "session": session,
            "clarification_needed": False,
            "clarification_prompt": None,
            "results": [],
        })

        # Persist updated session
        session_manager.update(payload.session_id, result["session"])

        # Build FileResult list
        file_results = [
            FileResult(**_normalise_file(r))
            for r in (result.get("results") or [])
        ]

        active_filters = {}
        intent = result.get("intent")
        if intent:
            active_filters = intent.active_filter_summary()

        return ChatResponse(
            session_id=payload.session_id,
            reply=result.get("reply") or "I couldn't process that request.",
            results=file_results,
            active_filters=active_filters,
            clarification_needed=result.get("clarification_needed", False),
            clarification_prompt=result.get("clarification_prompt"),
            open_file=FileResult(**_normalise_file(result["open_file"]))
            if result.get("open_file")
            else None,
        )

    except Exception:
        logger.exception(
            "Chat endpoint unhandled error",
            extra={"session_id": payload.session_id, "request_id": request_id},
        )
        raise HTTPException(status_code=500, detail="Internal server error")


def _normalise_file(raw: dict) -> dict:
    if not raw: return {}
    dt = raw.get("modified_time")
    ct = raw.get("created_time")
    return {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "mime_type": raw.get("mime_type", ""),
        "web_view_link": raw.get("web_view_link"),
        "modified_time": dt.isoformat() if hasattr(dt, "isoformat") else dt,
        "created_time": ct.isoformat() if hasattr(ct, "isoformat") else ct,
        "parent_folder_name": raw.get("parent_folder_name"),
        "size_bytes": raw.get("size_bytes"),
        "relevance_score": raw.get("relevance_score", 0.0),
        "match_reason": raw.get("match_reason", []),
        "is_duplicate": raw.get("is_duplicate", False),
        "similarity_group": raw.get("similarity_group"),
    }
