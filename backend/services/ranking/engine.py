"""
Intelligent 100-point relevance ranking engine with fuzzy matching.
"""
from __future__ import annotations

import math
import logging
import difflib
from datetime import datetime, timezone
from typing import List

from backend.schemas.drive import DriveFile
from backend.schemas.intent import SearchIntent

logger = logging.getLogger(__name__)


class RankingService:
    """
    Scoring components:
    - Name match (Exact: 60, Partial: 30, Fuzzy: up to 20)
    - Recency (25)
    - MIME relevance (10)
    - Ownership (5)
    """

    def rank(self, files: List[DriveFile], intent: SearchIntent) -> List[DriveFile]:
        scored = [self._compute_score(f, intent, i) for i, f in enumerate(files)]
        scored.sort(key=lambda f: (f.relevance_score, f.modified_time or datetime.min), reverse=True)
        return scored

    def _compute_score(self, f: DriveFile, intent: SearchIntent, position: int) -> DriveFile:
        reasons = []
        
        # 1. Filename Scoring
        name_score = 0.0
        fuzzy_score = 0.0
        
        query = intent.filename_query
        if query:
            name_lower = (f.name or "").lower()
            query_lower = query.lower()
            
            # Exact Match
            if name_lower == query_lower:
                name_score = 60.0
                reasons.append("exact name match")
            # Partial Match
            elif query_lower in name_lower:
                name_score = 30.0
                reasons.append("partial name match")
            # Fuzzy Similarity
            else:
                fuzzy_ratio = difflib.SequenceMatcher(None, query_lower, name_lower).ratio()
                if fuzzy_ratio > 0.6:
                    fuzzy_score = fuzzy_ratio * 20.0
                    reasons.append(f"fuzzy match ({int(fuzzy_ratio*100)}%)")

        # 2. MIME/Type relevance
        type_score = 0.0
        if f.mime_type in intent.mime_types:
            type_score = 10.0
            reasons.append("exact type match")
        elif any(ext in (f.name or "").lower() for ext in intent.file_extensions):
            type_score = 8.0
            reasons.append("extension match")

        # 3. Recency (30-day half-life)
        recency_score = 0.0
        if f.modified_time:
            age_days = max((datetime.now(timezone.utc) - f.modified_time).days, 0)
            decay = math.exp(-age_days / 43.3)
            recency_score = 25.0 * decay
            if recency_score > 15:
                reasons.append("recently modified")

        # 4. Ownership
        owner_score = 5.0 if f.owned_by_me else 0.0
        if owner_score > 0:
            reasons.append("your file")

        total = name_score + fuzzy_score + type_score + recency_score + owner_score
        f.relevance_score = round(min(total, 100.0), 2)
        f.match_reason = reasons
        
        return f
