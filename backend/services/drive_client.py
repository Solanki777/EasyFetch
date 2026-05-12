"""
Google Drive API client service.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import google.auth
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.config import settings
from backend.schemas.drive import DriveFile, DriveSearchParams

logger = logging.getLogger(__name__)


class DriveClient:
    """
    Wrapper for Google Drive API v3.
    """

    def __init__(self):
        self._creds = self._load_credentials()
        self._service = build(
            "drive",
            "v3",
            credentials=self._creds
        )
        self._recursive_folder_cache = {} # root_id -> (List[str], datetime)

    def _load_credentials(self):
        """
        Load credentials using Application Default Credentials (ADC).
        """

        creds, project = google.auth.default(
            scopes=[
                "https://www.googleapis.com/auth/drive.metadata.readonly"
            ]
        )

        return creds

    async def search(self, params: DriveSearchParams) -> List[DriveFile]:
        """
        Search Google Drive files.
        """

        if not self._service:
            return []

        try:
            # DEBUG
            logger.debug("\n===== DRIVE QUERY =====")
            logger.debug(f"Query: {params.q}")
            logger.debug(f"Root Restriction: {settings.google_drive_root_folder_id}")

            results = self._service.files().list(
                q=params.q,
                pageSize=params.page_size,
                orderBy=params.order_by,
                fields="files(id,name,mimeType,webViewLink,modifiedTime,size,owners,ownedByMe,parents)"

            ).execute()

            raw_files = results.get("files", [])

            print("\n===== RAW DRIVE RESULTS =====", flush=True)
            print(f"Files found: {len(raw_files)}", flush=True)

            files = []

            for f in raw_files:
                files.append(
                    DriveFile(
                        id=f.get("id"),
                        name=f.get("name"),
                        mime_type=f.get("mimeType"),
                        web_view_link=f.get("webViewLink"),
                        modified_time=f.get("modifiedTime"),
                        size_bytes=(
                            int(f.get("size"))
                            if f.get("size")
                            else None
                        ),
                        owned_by_me=f.get("ownedByMe", False),
                        parent_folder_id=(
                            f.get("parents")[0]
                            if f.get("parents")
                            else None
                        )
                    )
                )

            return files

        except HttpError as e:
            logger.error("Drive API error: %s", e)
            return []

    async def get_recursive_folder_ids(self, root_id: str) -> List[str]:
        """
        Recursively discover all subfolders under root_id using BFS.
        Results are cached for 5 minutes.
        """
        if not root_id:
            return []

        now = datetime.now()
        if root_id in self._recursive_folder_cache:
            ids, ts = self._recursive_folder_cache[root_id]
            if (now - ts).total_seconds() < 300:
                return ids

        logger.info(f"Starting recursive folder discovery for root: {root_id}")
        discovered = [root_id]
        queue = [root_id]

        try:
            while queue:
                current_parent = queue.pop(0)
                q = (
                    f"'{current_parent}' in parents "
                    f"and mimeType = 'application/vnd.google-apps.folder' "
                    f"and trashed = false"
                )
                
                # Fetch subfolders of current_parent
                results = self._service.files().list(
                    q=q,
                    fields="files(id, name)",
                    pageSize=100
                ).execute()
                
                for f in results.get("files", []):
                    fid = f.get("id")
                    if fid and fid not in discovered:
                        discovered.append(fid)
                        queue.append(fid)
                        logger.debug(f"Discovered subfolder: {f.get('name')} ({fid})")
            
            logger.info(f"Discovery complete. Total folders in hierarchy: {len(discovered)}")
            self._recursive_folder_cache[root_id] = (discovered, now)
            return discovered

        except HttpError as e:
            logger.error(f"Recursive folder discovery failed: {e}")
            # Fallback to at least returning the root ID if we have it
            return [root_id]

    async def get_folder_id(self, folder_name: str) -> Optional[str]:
        """
        Get Google Drive folder ID by folder name, restricted to the root hierarchy.
        """
        if not self._service:
            return None

        try:
            root_id = settings.google_drive_root_folder_id
            allowed_ids = []
            if root_id:
                allowed_ids = await self.get_recursive_folder_ids(root_id)

            q = (
                f"name = '{folder_name}' "
                f"and mimeType = 'application/vnd.google-apps.folder' "
                f"and trashed = false"
            )

            results = self._service.files().list(
                q=q,
                fields="files(id, parents)"
            ).execute()

            files = results.get("files", [])
            
            if not allowed_ids:
                return files[0].get("id") if files else None

            # Filter by allowed parents
            for f in files:
                parents = f.get("parents", [])
                if any(p in allowed_ids for p in parents):
                    return f.get("id")

            return None

        except HttpError as e:
            logger.error("Folder lookup failed: %s", e)
            return None

