"""
POST /api/v1/chat — main conversational search endpoint.
"""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.agent.graph import build_graph
from backend.dependencies import get_session_manager
from backend.schemas.api import (
    ChatRequest,
    ChatResponse,
    FileResult,
)
from backend.session.manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Compile graph once
_graph = build_graph()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
) -> ChatResponse:

    request_id = getattr(
        request.state,
        "request_id",
        "unknown"
    )

    try:

        print(
            f"--- Chat route triggered for session: {payload.session_id}",
            flush=True
        )

        session = session_manager.get_or_create(
            payload.session_id
        )

        result = await _graph.ainvoke({
            "user_message": payload.message,
            "session": session,
            "clarification_needed": False,
            "clarification_prompt": None,
            "results": [],
        })

        # Persist updated session
        session_manager.update(
            payload.session_id,
            result["session"]
        )

        # Normalize results
        file_results = []

        for r in (result.get("results") or []):

            normalized = _normalise_file(r)

            file_results.append(
                FileResult(**normalized)
            )

        # Active filters
        active_filters = {}

        intent = result.get("intent")

        if intent:
            try:
                active_filters = (
                    intent.active_filter_summary()
                )
            except Exception:
                active_filters = {}

        # Open file handling
        open_file = None

        if result.get("open_file"):

            normalized_open = _normalise_file(
                result["open_file"]
            )

            open_file = FileResult(
                **normalized_open
            )

        return ChatResponse(
            session_id=payload.session_id,

            reply=(
                result.get("reply")
                or "I couldn't process that request."
            ),

            results=file_results,

            active_filters=active_filters,

            clarification_needed=result.get(
                "clarification_needed",
                False
            ),

            clarification_prompt=result.get(
                "clarification_prompt"
            ),

            open_file=open_file,
        )

    except Exception:

        logger.exception(
            "Chat endpoint unhandled error",
            extra={
                "session_id": payload.session_id,
                "request_id": request_id
            },
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


def _normalise_file(raw):

    if raw is None:
        return {}

    # Convert Pydantic v2 model
    try:
        raw = raw.model_dump()
    except Exception:
        pass

    # Convert object -> dict
    if not isinstance(raw, dict):
        raw = vars(raw)

    dt = raw.get("modified_time")

    # Datetime -> ISO string
    if isinstance(dt, datetime):
        dt = dt.isoformat()

    return {
        "id": raw.get("id"),

        "name": raw.get("name"),

        "mime_type": raw.get(
            "mime_type"
        ),

        "web_view_link": raw.get(
            "web_view_link"
        ),

        "modified_time": dt,

        "size_bytes": raw.get(
            "size_bytes"
        ),

        "relevance_score": raw.get(
            "relevance_score",
            0
        ),

        "match_reason": raw.get(
            "match_reason",
            []
        ),

        "owned_by_me": raw.get(
            "owned_by_me",
            False
        ),

        "is_duplicate": raw.get(
            "is_duplicate",
            False
        ),

        "duplicate_group_id": raw.get(
            "duplicate_group_id"
        ),

        "similarity_group": raw.get(
            "similarity_group"
        ),
    }