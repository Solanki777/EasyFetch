"""
Universal Drive query builder with fallback support.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from backend.config import settings
from backend.schemas.drive import DriveSearchParams
from backend.schemas.intent import (
    SearchIntent,
    SortSpec,
    DateFilter,
    OwnerFilter,
)
from backend.utils.mime_types import get_mimes_for_query

logger = logging.getLogger(__name__)


class QueryBuilder:
    """
    Converts SearchIntent -> Drive API q string.
    Supports fallback modes: 'strict', 'broad', 'contains'.
    """

    STOPWORDS = {"show", "find", "search", "give", "list", "files", "get", "me", "all", "the", "a", "an"}

    def build(
        self,
        intent: SearchIntent,
        allowed_folder_ids: Optional[List[str]] = None,
        mode: str = "strict"  # strict, broad, contains
    ) -> DriveSearchParams:
        """
        Build Google Drive q query based on mode.
        """
        clauses = []

        # ── HIERARCHY RESTRICTION ────────────────────────────────────
        if allowed_folder_ids:
            parent_parts = [f"'{fid}' in parents" for fid in allowed_folder_ids]
            if len(parent_parts) > 1:
                clauses.append(f"({' or '.join(parent_parts)})")
            else:
                clauses.append(parent_parts[0])
        elif settings.google_drive_root_folder_id:
            clauses.append(f"'{settings.google_drive_root_folder_id}' in parents")

        # ── FOLDER FILTER ────────────────────────────────────────────
        # Handled via allowed_folder_ids recursive injection in nodes.py

        # ── MIME TYPES ───────────────────────────────────────────────
        mimes = set(intent.mime_types)
        # Add mimes from extensions
        for ext in intent.file_extensions:
            mimes.update(get_mimes_for_query(ext))
            
        if mimes:
            mime_parts = [f"mimeType = '{m}'" for m in mimes]
            if len(mime_parts) > 1:
                clauses.append(f"({' or '.join(mime_parts)})")
            else:
                clauses.append(mime_parts[0])

        # ── FILENAME SEARCH ──────────────────────────────────────────
        name_query = intent.filename_query
        if name_query:
            cleaned = self._clean_query(name_query)
            if cleaned:
                safe = self._escape(cleaned)
                if mode == "strict":
                    clauses.append(f"name = '{safe}'")
                elif mode == "broad":
                    # For broad, we use 'contains' but can add more logic later
                    clauses.append(f"name contains '{safe}'")
                else: # contains
                    clauses.append(f"name contains '{safe}'")

        # ── CONTENT SEARCH ──────────────────────────────────────────
        if intent.search_in_content and intent.fulltext_query:
            safe_text = self._escape(intent.fulltext_query)
            clauses.append(f"fullText contains '{safe_text}'")

        # ── DATE & OWNER ─────────────────────────────────────────────
        if intent.date_filter:
            clauses.extend(self._build_date_clauses(intent.date_filter))
        if intent.owner_filter:
            clauses.extend(self._build_owner_clauses(intent.owner_filter))

        clauses.append("trashed = false")

        q = " and ".join(clauses)
        order_by = self._build_order_by(intent.sort)

        return DriveSearchParams(
            q=q,
            order_by=order_by,
            page_size=max(intent.result_limit * 2, 20)
        )

    def _clean_query(self, query: str) -> str:
        words = query.split()
        filtered = [w for w in words if w.lower() not in self.STOPWORDS]
        return " ".join(filtered)

    def _build_date_clauses(self, df: DateFilter) -> List[str]:
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

    def _build_owner_clauses(self, owner: OwnerFilter) -> List[str]:
        clauses = []
        if owner.owned_by_me: clauses.append("'me' in owners")
        if owner.shared_with_me: clauses.append("sharedWithMe = true")
        if owner.owner_email:
            safe = self._escape(owner.owner_email)
            clauses.append(f"'{safe}' in owners")
        return clauses

    def _build_order_by(self, sort: SortSpec) -> str:
        field_map = {"modifiedTime": "modifiedTime", "createdTime": "createdTime", "name": "name"}
        field = field_map.get(sort.field, "modifiedTime")
        direction = " desc" if sort.direction == "desc" else ""
        return f"{field}{direction}"

    def _resolve_relative(self, relative: str) -> tuple:
        now = datetime.now(timezone.utc)
        def start_of_day(dt): return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        mapping = {
            "today": (start_of_day(now), now),
            "yesterday": (start_of_day(now - relativedelta(days=1)), start_of_day(now)),
            "this_week": (now - relativedelta(weeks=1), now),
            "last_week": (now - relativedelta(weeks=2), now - relativedelta(weeks=1)),
            "this_month": (now - relativedelta(months=1), now),
            "this_year": (now.replace(month=1, day=1, hour=0, minute=0, second=0), now),
        }
        return mapping.get(relative, (None, None))

    def _escape(self, s: str) -> str:
        return s.replace("'", "\\'")
