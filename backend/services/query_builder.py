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

    def build(self, intent: SearchIntent) -> DriveSearchParams:
        clauses = []

        if intent.folder_id:
            clauses.append(f"'{intent.folder_id}' in parents")

        if intent.mime_types or intent.file_extensions:
            mimes = set(intent.mime_types)
            for ext in intent.file_extensions:
                mime = EXTENSION_TO_MIME.get(ext)
                if mime: mimes.add(mime)
            if mimes:
                mime_parts = [f"mimeType = '{m}'" for m in mimes]
                clauses.append(f"({' or '.join(mime_parts)})")

        if intent.filename_query:
            safe_name = self._escape(intent.filename_query)
            clauses.append(f"name contains '{safe_name}'")

        if intent.search_in_content and intent.fulltext_query:
            safe_text = self._escape(intent.fulltext_query)
            clauses.append(f"fullText contains '{safe_text}'")

        if intent.date_filter:
            clauses.extend(self._build_date_clauses(intent.date_filter))

        if intent.owner_filter:
            clauses.extend(self._build_owner_clauses(intent.owner_filter))

        # Always exclude trashed
        clauses.append("trashed = false")

        q = " and ".join(clauses)
        order_by = self._build_order_by(intent.sort)

        return DriveSearchParams(
            q=q,
            order_by=order_by,
            page_size=intent.result_limit * 2  # headroom for ranking
        )

    def _build_date_clauses(self, df) -> List[str]:
        clauses = []
        field = df.field
        if df.relative:
            after, before = self._resolve_relative(df.relative)
            if after: clauses.append(f"{field} >= '{after.isoformat()}'")
            if before: clauses.append(f"{field} <= '{before.isoformat()}'")
        elif df.explicit:
            if df.explicit.after: clauses.append(f"{field} >= '{df.explicit.after.isoformat()}'")
            if df.explicit.before: clauses.append(f"{field} <= '{df.explicit.before.isoformat()}'")
        return clauses

    def _build_owner_clauses(self, owner) -> List[str]:
        clauses = []
        if owner.owned_by_me: clauses.append("'me' in owners")
        if owner.shared_with_me: clauses.append("sharedWithMe = true")
        if owner.owner_email:
            safe_email = self._escape(owner.owner_email)
            clauses.append(f"'{safe_email}' in owners")
        return clauses

    def _build_order_by(self, sort: SortSpec) -> str:
        field_map = {
            "modifiedTime": "modifiedTime",
            "createdTime": "createdTime",
            "name": "name",
            "relevance": "modifiedTime"
        }
        field = field_map.get(sort.field, "modifiedTime")
        direction = " desc" if sort.direction == "desc" else ""
        return f"{field}{direction}"

    def _resolve_relative(self, relative: str) -> tuple:
        now = datetime.now(timezone.utc)
        mapping = {
            "today":         (now.replace(hour=0, minute=0, second=0), now),
            "yesterday":     (now.replace(hour=0, minute=0, second=0) - relativedelta(days=1),
                              now.replace(hour=0, minute=0, second=0)),
            "this_week":     (now - relativedelta(weeks=1), now),
            "last_week":     (now - relativedelta(weeks=2), now - relativedelta(weeks=1)),
            "this_month":    (now - relativedelta(months=1), now),
            "last_month":    (now - relativedelta(months=2), now - relativedelta(months=1)),
            "this_year":     (now.replace(month=1, day=1, hour=0, minute=0, second=0), now),
        }
        return mapping.get(relative, (None, None))

    def _escape(self, s: str) -> str:
        return s.replace("'", "\\'")
