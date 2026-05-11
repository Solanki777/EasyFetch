"""
100-point relevance ranking engine.
"""
from __future__ import annotations

import math
import logging
from datetime import datetime, timezone
from typing import List

from backend.schemas.drive import DriveFile
from backend.schemas.intent import SearchIntent

logger = logging.getLogger(__name__)


class RankingService:
    """
    Scoring components:
    - Name match (35)
    - Recency (25)
    - Position signal (15)
    - Type match (10)
    - Content signal (5)
    - Ownership bonus (5)
    - Completeness (5)
    """

    def rank(self, files: List[DriveFile], intent: SearchIntent) -> List[DriveFile]:
        scored = [self._compute_score(f, intent, i) for i, f in enumerate(files)]
        scored.sort(key=lambda f: (f.relevance_score, f.modified_time or datetime.min), reverse=True)
        return scored

    def _compute_score(self, f: DriveFile, intent: SearchIntent, position: int) -> DriveFile:
        name_score = self._score_name(f, intent)
        recency_score = self._score_recency(f)
        pos_score = self._score_position(position)
        type_score = self._score_type(f, intent)
        owner_score = self._score_ownership(f)
        comp_score = self._score_completeness(f)

        total = name_score + recency_score + pos_score + type_score + owner_score + comp_score
        f.relevance_score = round(min(total, 100.0), 2)
        
        # Populate match reasons
        reasons = []
        if name_score >= 20: reasons.append("strong name match")
        elif name_score > 5: reasons.append("partial name match")
        if recency_score >= 15: reasons.append("recently modified")
        if type_score >= 10: reasons.append("exact type match")
        if owner_score >= 5: reasons.append("your file")
        
        f.match_reason = reasons
        return f

    def _score_name(self, f: DriveFile, intent: SearchIntent) -> float:
        query = intent.filename_query
        if not query: return 0.0
        name, q = f.name.lower(), query.lower()
        if name == q: return 35.0
        if name.startswith(q): return 29.0
        if q in name: return 21.0
        return 0.0

    def _score_recency(self, f: DriveFile) -> float:
        if not f.modified_time: return 0.0
        age_days = max((datetime.now(timezone.utc) - f.modified_time).days, 0)
        decay = math.exp(-age_days / 43.3)  # 30-day half-life
        return 25.0 * decay

    def _score_position(self, position: int) -> float:
        return 15.0 * math.exp(-position / 15.0)

    def _score_type(self, f: DriveFile, intent: SearchIntent) -> float:
        if f.mime_type in intent.mime_types: return 10.0
        ext = f.name.split('.')[-1].lower() if '.' in f.name else ''
        if ext in intent.file_extensions: return 8.0
        return 0.0

    def _score_ownership(self, f: DriveFile) -> float:
        return 5.0 if f.owned_by_me else 0.0

    def _score_completeness(self, f: DriveFile) -> float:
        score = 0.0
        if f.web_view_link: score += 2.0
        if f.size_bytes: score += 2.0
        if f.parent_folder_name: score += 1.0
        return score
