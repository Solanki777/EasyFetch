"""
In-memory session store with TTL eviction.

Thread-safe for single-process deployments (uvicorn --workers 1).
Swap SessionManager for RedisSessionManager when scaling horizontally.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Dict, Optional, Tuple

from backend.schemas.session import SessionState

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Stores SessionState objects keyed by session_id.
    Evicts sessions that have been idle longer than ttl_seconds.
    """

    def __init__(self, ttl_seconds: int = 3600):
        # Value: (SessionState, last_touched_timestamp)
        self._store: Dict[str, Tuple[SessionState, float]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    # ── Public API ────────────────────────────────────────────────────────────

    def get_or_create(self, session_id: Optional[str] = None) -> SessionState:
        with self._lock:
            self._evict_expired()
            sid = session_id or str(uuid.uuid4())

            if sid in self._store:
                session, _ = self._store[sid]
                self._store[sid] = (session, time.time())
                return session

            session = SessionState(session_id=sid)
            self._store[sid] = (session, time.time())
            logger.info("Session created", extra={"session_id": sid})
            return session

    def update(self, session_id: str, session: SessionState) -> None:
        with self._lock:
            self._store[session_id] = (session, time.time())

    def get(self, session_id: str) -> Optional[SessionState]:
        with self._lock:
            entry = self._store.get(session_id)
            if entry:
                session, _ = entry
                self._store[session_id] = (session, time.time())
                return session
            return None

    def delete(self, session_id: str) -> bool:
        with self._lock:
            existed = session_id in self._store
            self._store.pop(session_id, None)
            return existed

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [sid for sid, (_, ts) in self._store.items() if now - ts > self._ttl]
        for sid in expired:
            del self._store[sid]
            logger.info("Session evicted (TTL expired)", extra={"session_id": sid})
