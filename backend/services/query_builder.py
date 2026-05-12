"""
Deterministic Drive query builder.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from backend.schemas.drive import DriveSearchParams
from backend.schemas.intent import SearchIntent, SortSpec
from backend.utils.mime_types import EXTENSION_TO_MIME

logger = logging.getLogger(__name__)


class QueryBuilder:
    """
    Converts SearchIntent -> Drive API q string.
    """

    STOPWORDS = {
        "show", "find", "search", "give", "list", "files", "documents",
        "stuff", "get", "me", "all", "everything", "any", "the", "a", "an"
    }

    def build(self, intent: SearchIntent) -> DriveSearchParams:
        """
        Builds a Google Drive search query from intent.
        """
        clauses = []

        # 1. Folder filter
        if intent.folder_id:
            clauses.append(f"'{intent.folder_id}' in parents")

        # 2. MIME type filters (Multi-MIME Support)
        mimes = set(intent.mime_types)
        for ext in intent.file_extensions:
            mime = EXTENSION_TO_MIME.get(ext.lower())
            if mime:
                mimes.add(mime)

        if mimes:
            mime_parts = [f"mimeType = '{m}'" for m in mimes]
            if len(mime_parts) > 1:
                clauses.append(f"({' or '.join(mime_parts)})")
            else:
                clauses.append(mime_parts[0])

        # 3. Filename search (Sanitized & Cleaned)
        name_query = intent.filename_query
        if name_query:
            cleaned_name = self._clean_query(name_query)
            if cleaned_name:
                safe_name = self._escape(cleaned_name)
                clauses.append(f"name contains '{safe_name}'")

        # 4. Full text search
        if intent.search_in_content and intent.fulltext_query:
            safe_text = self._escape(intent.fulltext_query)
            clauses.append(f"fullText contains '{safe_text}'")
        elif intent.fulltext_query:
            # Fallback if search_in_content is false but fulltext_query exists
            safe_text = self._escape(intent.fulltext_query)
            clauses.append(f"fullText contains '{safe_text}'")

        # 5. Date filters
        if intent.date_filter:
            clauses.extend(self._build_date_clauses(intent.date_filter))

        # 6. Owner filters
        if intent.owner_filter:
            clauses.extend(self._build_owner_clauses(intent.owner_filter))

        # Always exclude trashed files
        clauses.append("trashed = false")

        # Final query assembly
        q = " and ".join(clauses)

        # Logging for observability
        logger.info(f"Generated Drive Query: [ {q} ]")
        if intent.sort:
            logger.info(f"Sort: {intent.sort.field} {intent.sort.direction}")

        order_by = self._build_order_by(intent.sort)

        return DriveSearchParams(
            q=q,
            order_by=order_by,
            page_size=intent.result_limit * 2
        )

    def _clean_query(self, query: str) -> str:
        """Removes generic verbs and filler words from the query."""
        words = query.lower().split()
        filtered = [w for w in words if w not in self.STOPWORDS]
        return " ".join(filtered)

    def _build_date_clauses(self, df: DateFilter) -> List[str]:
        clauses = []
        field = df.field

        if df.relative:
            after, before = self._resolve_relative(df.relative)
            if after:
                clauses.append(f"{field} >= '{after.isoformat()}'")
            if before:
                clauses.append(f"{field} <= '{before.isoformat()}'")
        elif df.explicit:
            if df.explicit.after:
                clauses.append(f"{field} >= '{df.explicit.after.isoformat()}'")
            if df.explicit.before:
                clauses.append(f"{field} <= '{df.explicit.before.isoformat()}'")

        return clauses

    def _build_owner_clauses(self, owner: OwnerFilter) -> List[str]:
        clauses = []
        if owner.owned_by_me:
            clauses.append("'me' in owners")
        if owner.shared_with_me:
            clauses.append("sharedWithMe = true")
        if owner.owner_email:
            safe_email = self._escape(owner.owner_email)
            clauses.append(f"'{safe_email}' in owners")
        return clauses

    def _build_order_by(self, sort: SortSpec) -> str:
        field_map = {
            "modifiedTime": "modifiedTime",
            "createdTime": "createdTime",
            "name": "name",
            "relevance": "modifiedTime" # Drive API relevance doesn't have a direct sort field in order_by the same way
        }

        field = field_map.get(sort.field, "modifiedTime")
        direction = " desc" if sort.direction == "desc" else ""
        return f"{field}{direction}"

    def _resolve_relative(self, relative: str) -> tuple:
        now = datetime.now(timezone.utc)
        
        # Helper for start of day
        def start_of_day(dt):
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)

        mapping = {
            "today": (start_of_day(now), now),
            "yesterday": (start_of_day(now - relativedelta(days=1)), start_of_day(now)),
            "this_week": (now - relativedelta(weeks=1), now),
            "last_week": (now - relativedelta(weeks=2), now - relativedelta(weeks=1)),
            "this_month": (now - relativedelta(months=1), now),
            "last_month": (now - relativedelta(months=2), now - relativedelta(months=1)),
            "this_year": (now.replace(month=1, day=1, hour=0, minute=0, second=0), now),
        }

        return mapping.get(relative, (None, None))

    def _escape(self, s: str) -> str:
        return s.replace("'", "\\'")


