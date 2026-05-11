"""
GET  /api/v1/session/{session_id} — inspect session state
DELETE /api/v1/session/{session_id} — clear a session
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_session_manager
from backend.schemas.api import SessionInfoResponse
from backend.session.manager import SessionManager

router = APIRouter()


@router.get("/session/{session_id}", response_model=SessionInfoResponse)
async def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionInfoResponse:
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    active = {}
    if session.active_filters:
        active = session.active_filters.model_dump(exclude_none=True, exclude={"raw_query"})

    return SessionInfoResponse(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
        last_active=session.last_active.isoformat(),
        turn_count=len(session.history),
        active_filters=active,
        last_results_count=len(session.last_results),
    )


@router.delete("/session/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
) -> None:
    found = session_manager.delete(session_id)
    if not found:
        raise HTTPException(status_code=404, detail="Session not found")
