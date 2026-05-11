"""API request / response schemas for the chat endpoint."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str = Field(..., min_length=1, max_length=2000)


class FileResult(BaseModel):
    """Serialised DriveFile for API responses (no internal post-processing fields)."""

    id: str
    name: str
    mime_type: str
    web_view_link: Optional[str] = None
    modified_time: Optional[str] = None
    created_time: Optional[str] = None
    parent_folder_name: Optional[str] = None
    size_bytes: Optional[int] = None
    relevance_score: float
    match_reason: List[str]
    is_duplicate: bool
    similarity_group: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    results: List[FileResult] = []
    active_filters: Dict[str, Any] = {}
    clarification_needed: bool = False
    clarification_prompt: Optional[str] = None
    result_count: int = 0

    # file to open (populated when followup_action == "open_file")
    open_file: Optional[FileResult] = None

    @model_validator(mode="after")
    def set_result_count(self) -> "ChatResponse":
        self.result_count = len(self.results)
        return self


class SessionInfoResponse(BaseModel):
    session_id: str
    created_at: str
    last_active: str
    turn_count: int
    active_filters: Dict[str, Any]
    last_results_count: int


class HealthResponse(BaseModel):
    status: str
    version: str
    session_count: int
