"""
Session state schemas — persisted per user conversation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from backend.schemas.drive import DriveFile
from backend.schemas.intent import SearchIntent


class ConversationTurn(BaseModel):
    turn_id: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_message: str
    assistant_reply: str
    intent_snapshot: Optional[SearchIntent] = None
    result_count: int = 0


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    history: List[ConversationTurn] = []
    active_filters: Optional[SearchIntent] = None
    last_results: List[DriveFile] = []
    
    # Caches
    folder_cache: Dict[str, str] = {}  # name -> id

    def add_turn(
        self,
        user_msg: str,
        reply: str,
        results_count: int = 0,
        intent: Optional[SearchIntent] = None
    ) -> None:
        turn = ConversationTurn(
            turn_id=len(self.history) + 1,
            user_message=user_msg,
            assistant_reply=reply,
            intent_snapshot=intent,
            result_count=results_count
        )
        self.history.append(turn)
        self.last_active = datetime.now(timezone.utc)

    def get_file_by_index(self, index: int) -> Optional[DriveFile]:
        """Resolve 1-based index into a file from last_results."""
        if 0 < index <= len(self.last_results):
            return self.last_results[index - 1]
        return None
