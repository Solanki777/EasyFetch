"""FastAPI dependency injection providers."""
from __future__ import annotations

from fastapi import Request

from backend.session.manager import SessionManager


def get_session_manager(request: Request) -> SessionManager:
    """Retrieve the SessionManager attached to app.state."""
    return request.app.state.session_manager
