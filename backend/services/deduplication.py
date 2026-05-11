"""
Deduplication heuristics.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Tuple, Dict
from collections import defaultdict

from backend.schemas.drive import DriveFile


class DeduplicationService:
    """
    Level 1: Exact ID dedup
    Level 2: Same name + same folder (keeps newest)
    Level 3: Near-duplicate grouping (versions)
    """

    def deduplicate(self, files: List[DriveFile]) -> List[DriveFile]:
        if not files: return []

        # Level 1: ID dedup
        unique_by_id = {}
        for f in files:
            if f.id not in unique_by_id:
                unique_by_id[f.id] = f
        
        # Level 2: Same name + same folder
        groups = defaultdict(list)
        for f in unique_by_id.values():
            key = f"{f.name.lower()}::{f.parent_folder_id or 'root'}"
            groups[key].append(f)

        kept = []
        for group in groups.values():
            if len(group) == 1:
                kept.append(group[0])
            else:
                # Keep newest
                sorted_group = sorted(
                    group,
                    key=lambda x: x.modified_time or datetime.min,
                    reverse=True
                )
                master = sorted_group[0]
                master.duplicate_group_id = master.id
                kept.append(master)
                # Mark others as duplicates
                for other in sorted_group[1:]:
                    other.is_duplicate = True
                    other.duplicate_group_id = master.id

        return kept
