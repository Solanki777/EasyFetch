"""Async httpx client for the FastAPI backend."""
from __future__ import annotations

import os
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 30.0


class APIClient:
    """Thin synchronous wrapper (httpx) used from Streamlit."""

    def __init__(self, base_url: str = BACKEND_URL):
        self._base = base_url.rstrip("/")

    def chat(self, session_id: str, message: str) -> dict:
        """POST /api/v1/chat and return the parsed JSON response."""
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(
                f"{self._base}/api/v1/chat",
                json={"session_id": session_id, "message": message},
            )
            resp.raise_for_status()
            return resp.json()

    def get_session(self, session_id: str) -> dict | None:
        """GET /api/v1/session/{id}"""
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self._base}/api/v1/session/{session_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    def delete_session(self, session_id: str) -> bool:
        with httpx.Client(timeout=10.0) as client:
            resp = client.delete(f"{self._base}/api/v1/session/{session_id}")
            return resp.status_code == 204

    def health(self) -> dict:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{self._base}/health")
            resp.raise_for_status()
            return resp.json()
