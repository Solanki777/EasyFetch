"""
Optional Redis-backed session store.

Drop-in replacement for SessionManager — same public interface.
Enable by setting REDIS_URL in .env.

Serialises SessionState to JSON via Pydantic's model_dump_json().
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class RedisSessionManager:
    """Redis-backed session manager. Requires: pip install redis"""

    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        import redis
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl_seconds
        logger.info("RedisSessionManager initialised", extra={"url": redis_url})

    def get_or_create(self, session_id: Optional[str] = None):
        from backend.schemas.session import SessionState
        sid = session_id or str(uuid.uuid4())
        raw = self._client.get(self._key(sid))
        if raw:
            session = SessionState.model_validate_json(raw)
            self._client.expire(self._key(sid), self._ttl)
            return session
        session = SessionState(session_id=sid)
        self._save(session)
        return session

    def update(self, session_id: str, session) -> None:
        self._save(session)

    def get(self, session_id: str):
        from backend.schemas.session import SessionState
        raw = self._client.get(self._key(session_id))
        if raw:
            return SessionState.model_validate_json(raw)
        return None

    def delete(self, session_id: str) -> bool:
        return bool(self._client.delete(self._key(session_id)))

    def count(self) -> int:
        return len(self._client.keys("session:*"))

    def _save(self, session) -> None:
        self._client.setex(
            self._key(session.session_id),
            self._ttl,
            session.model_dump_json(),
        )

    @staticmethod
    def _key(session_id: str) -> str:
        return f"session:{session_id}"
