from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class DateBoundary(BaseModel):
    """Explicit date range. Mutually exclusive with `relative`."""
    after: Optional[datetime] = None
    before: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.after and self.before and self.after >= self.before:
            raise ValueError("after must be earlier than before")
        return self


class DateFilter(BaseModel):
    """
    Two modes: relative (human-friendly) or explicit (precise).
    """
    relative: Optional[Literal[
        "today", "yesterday", "this_week", "last_week",
        "this_month", "last_month", "this_quarter", "this_year", "last_year"
    ]] = None
    explicit: Optional[DateBoundary] = None
    field: Literal["modifiedTime", "createdTime", "viewedByMeTime"] = "modifiedTime"

    @model_validator(mode="after")
    def validate_exclusive(self):
        if self.relative and self.explicit:
            raise ValueError("Cannot specify both relative and explicit date filter")
        return self


class SortSpec(BaseModel):
    field: Literal["modifiedTime", "createdTime", "name", "relevance"] = "modifiedTime"
    direction: Literal["asc", "desc"] = "desc"


class OwnerFilter(BaseModel):
    """Filter by file ownership."""
    owned_by_me: Optional[bool] = None
    shared_with_me: Optional[bool] = None
    owner_email: Optional[str] = None


class SizeFilter(BaseModel):
    min_bytes: Optional[int] = None
    max_bytes: Optional[int] = None


class FollowUpContext(BaseModel):
    """Tracks the nature of a follow-up for deterministic merging."""
    is_followup: bool = False
    action: Optional[Literal[
        "filter_mime", "filter_date", "filter_folder", "filter_owner",
        "sort", "expand_results", "narrow_query", "search_content",
        "open_file", "remove_filter", "new_search", "clarify_response"
    ]] = None
    open_file_ref: Optional[str] = None
    open_file_index: Optional[int] = None
    removed_filter: Optional[str] = None


class AmbiguitySignal(BaseModel):
    needs_clarification: bool = False
    ambiguity_type: Optional[Literal[
        "vague_query", "ambiguous_type", "ambiguous_date",
        "ambiguous_folder", "too_broad", "conflicting_signals"
    ]] = None
    clarification_question: Optional[str] = None
    suggested_options: List[str] = []


class SearchIntent(BaseModel):
    """
    The fully-specified, validated intent for a single Drive search turn.
    """
    filename_query: Optional[str] = Field(None, max_length=200)
    fulltext_query: Optional[str] = Field(None, max_length=500)
    search_in_content: bool = False

    mime_types: List[str] = Field(default_factory=list)
    file_extensions: List[str] = Field(default_factory=list)
    excluded_mime_types: List[str] = Field(default_factory=list)

    date_filter: Optional[DateFilter] = None
    folder_name: Optional[str] = None
    folder_id: Optional[str] = None
    drive_id: Optional[str] = None
    search_scope: Literal["user", "drive", "allDrives"] = "user"

    owner_filter: Optional[OwnerFilter] = None
    size_filter: Optional[SizeFilter] = None

    sort: SortSpec = Field(default_factory=SortSpec)
    result_limit: int = Field(10, ge=1, le=50)

    followup: FollowUpContext = Field(default_factory=FollowUpContext)
    ambiguity: AmbiguitySignal = Field(default_factory=AmbiguitySignal)

    raw_query: str = ""
    intent_version: str = "1.1"
    extraction_confidence: float = Field(1.0, ge=0.0, le=1.0)

    @field_validator("file_extensions", mode="before")
    @classmethod
    def normalize_extensions(cls, v):
        return [ext.lower().lstrip(".") for ext in (v or [])]

    @field_validator("filename_query", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        return v.strip() if v else v

    def is_empty(self) -> bool:
        return (
            not self.filename_query and not self.fulltext_query
            and not self.mime_types and not self.file_extensions
            and not self.date_filter and not self.folder_id
        )

    def active_filter_summary(self) -> dict:
        filters = {}
        if self.filename_query: filters["name"] = self.filename_query
        if self.file_extensions: filters["type"] = ", ".join(e.upper() for e in self.file_extensions)
        if self.date_filter: filters["date"] = self.date_filter.relative or "custom range"
        if self.folder_name: filters["folder"] = self.folder_name
        if self.search_in_content: filters["content_search"] = "on"
        return filters
