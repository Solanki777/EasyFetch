"""
Deterministic follow-up refinement merge logic.
"""
from __future__ import annotations

import logging
from typing import Optional

from backend.schemas.intent import SearchIntent

logger = logging.getLogger(__name__)


class FollowUpMerger:
    """
    Deterministic follow-up merger.
    
    Design invariants:
    - Never mutates either input
    - Returns a new SearchIntent
    """

    def merge(
        self,
        base: SearchIntent,
        update: SearchIntent,
    ) -> SearchIntent:
        action = update.followup.action

        if action == "new_search" or not base:
            return update

        merged = base.model_copy(deep=True)
        merged.raw_query = update.raw_query
        merged.followup = update.followup

        dispatch = {
            "filter_mime":    self._merge_mime,
            "filter_date":    self._merge_date,
            "filter_folder":  self._merge_folder,
            "filter_owner":   self._merge_owner,
            "sort":           self._merge_sort,
            "expand_results": self._merge_expand,
            "narrow_query":   self._merge_narrow,
            "search_content": self._merge_content,
            "remove_filter":  self._merge_remove,
            "open_file":      self._merge_open,
            "clarify_response": self._merge_clarify,
        }

        handler = dispatch.get(action, self._merge_best_effort)
        merged = handler(merged, update)

        # Safety: never produce an unrestricted scan
        if merged.is_empty():
            merged.ambiguity.needs_clarification = True
            merged.ambiguity.clarification_question = (
                "After those changes, the search has no specific criteria. "
                "What would you like to look for?"
            )

        return merged

    def _merge_mime(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        merged.mime_types = update.mime_types
        merged.file_extensions = update.file_extensions
        merged.excluded_mime_types = update.excluded_mime_types
        return merged

    def _merge_date(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        merged.date_filter = update.date_filter
        return merged

    def _merge_folder(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        merged.folder_name = update.folder_name
        merged.folder_id = update.folder_id
        merged.drive_id = update.drive_id
        merged.search_scope = update.search_scope
        return merged

    def _merge_owner(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        merged.owner_filter = update.owner_filter
        return merged

    def _merge_sort(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        merged.sort = update.sort
        return merged

    def _merge_expand(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        merged.result_limit = min((merged.result_limit or 10) + 10, 50)
        return merged

    def _merge_narrow(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        if update.filename_query:
            merged.filename_query = update.filename_query
        return merged

    def _merge_content(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        merged.search_in_content = True
        merged.fulltext_query = update.fulltext_query or merged.filename_query
        return merged

    def _merge_remove(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        field = update.followup.removed_filter
        removable = {
            "date": "date_filter",
            "type": ("mime_types", "file_extensions"),
            "folder": ("folder_name", "folder_id"),
            "name": "filename_query",
            "owner": "owner_filter",
            "content": ("search_in_content", "fulltext_query"),
        }
        targets = removable.get(field)
        if isinstance(targets, str):
            setattr(merged, targets, None)
        elif isinstance(targets, tuple):
            for t in targets:
                attr = getattr(merged, t)
                if isinstance(attr, list): setattr(merged, t, [])
                else: setattr(merged, t, None if not isinstance(attr, bool) else False)
        return merged

    def _merge_open(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        merged.followup.open_file_index = update.followup.open_file_index
        return merged

    def _merge_clarify(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        return self._merge_best_effort(merged, update)

    def _merge_best_effort(self, merged: SearchIntent, update: SearchIntent) -> SearchIntent:
        skip = {"followup", "raw_query", "intent_version", "extraction_confidence", "ambiguity"}
        for field, value in update.model_dump(exclude_none=True).items():
            if field not in skip and value:
                setattr(merged, field, value)
        return merged


def merge_followup(base: SearchIntent, update: SearchIntent) -> SearchIntent:
    """Convenience functional wrapper for the class-based merger."""
    return FollowUpMerger().merge(base, update)
