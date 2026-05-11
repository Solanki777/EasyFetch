"""Schemas for Google Drive file objects and search parameters."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DriveFile(BaseModel):
    """A single Google Drive file, enriched with post-processing metadata."""

    # ── Core Drive fields ─────────────────────────────────────────────────────
    id: str
    name: str
    mime_type: str
    web_view_link: Optional[str] = None
    modified_time: Optional[datetime] = None
    created_time: Optional[datetime] = None
    size_bytes: Optional[int] = None
    parent_folder_id: Optional[str] = None
    parent_folder_name: Optional[str] = None
    owners: List[str] = []
    shared: bool = False
    owned_by_me: bool = False

    # ── Post-processing fields (populated by ranking / dedup / grouping) ──────
    relevance_score: float = 0.0
    match_reason: List[str] = []
    is_duplicate: bool = False
    duplicate_group_id: Optional[str] = None
    similarity_group: Optional[str] = None


class DriveSearchParams(BaseModel):
    """Validated parameters passed to the Drive API files.list() call."""

    q: str
    order_by: str = "modifiedTime desc"
    page_size: int = 50
    fields: str = (
        "files(id,name,mimeType,webViewLink,modifiedTime,createdTime,"
        "size,parents,owners,shared)"
    )
    corpora: str = "user"
