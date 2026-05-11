"""
Grouping results for UI display.
"""
from __future__ import annotations

from typing import Dict, List
from collections import defaultdict

from backend.schemas.drive import DriveFile


class GroupingService:
    """
    Groups results by folder by default.
    """

    def group(self, files: List[DriveFile]) -> Dict[str, List[DriveFile]]:
        if not files: return {}
        groups = defaultdict(list)
        for f in files:
            folder = f.parent_folder_name or "My Drive"
            groups[folder].append(f)
        return dict(groups)
