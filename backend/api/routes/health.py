"""GET /health — liveness probe."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.config import settings
from backend.dependencies import get_session_manager
from backend.schemas.api import HealthResponse
from backend.session.manager import SessionManager

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(
    session_manager: SessionManager = Depends(get_session_manager),
) -> HealthResponse:
    print("[BACKEND] Health check request received", flush=True)
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        session_count=session_manager.count(),
    )
