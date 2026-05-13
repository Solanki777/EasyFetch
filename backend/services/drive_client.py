
"""
Google Drive API client service.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.config import settings
from backend.schemas.drive import (
    DriveFile,
    DriveSearchParams,
)

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

        self._recursive_folder_cache = {}

    # ────────────────────────────────────────────────────────────────
    
    def _load_credentials(self):
        """
        Load credentials from:
        1. Railway env variable
        2. Local service_account.json fallback
        """

        # Try production env variable first
        env_json = (
            settings.google_service_account_json_content
            or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT")
        )

        try:
            if env_json and env_json.strip() and env_json.strip().startswith("{"):
                try:
                    service_account_info = json.loads(env_json)
                    creds = service_account.Credentials.from_service_account_info(
                        service_account_info,
                        scopes=["https://www.googleapis.com/auth/drive.readonly"]
                    )
                    logger.info("Loaded Google credentials from JSON content (Production)")
                    return creds
                except json.JSONDecodeError:
                    logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT is not valid JSON, falling back")

            # ── Local Development Fallback ─────────────────────
            try:
                creds = service_account.Credentials.from_service_account_file(
                    settings.google_service_account_json,
                    scopes=["https://www.googleapis.com/auth/drive.readonly"]
                )
                logger.info("Loaded Google credentials from local file")
                return creds
            except ValueError as ve:
                if "installed" in str(ve) or "client_id" in str(ve):
                    logger.error("The file in credentials/service_account.json appears to be an OAuth Client ID, not a Service Account key.")
                raise ve

        except Exception as e:
            logger.error(f"Failed loading Google credentials: {e}")
            raise e


    # ────────────────────────────────────────────────────────────────

    async def search(
        self,
        params: DriveSearchParams
    ) -> List[DriveFile]:

        try:

            import time
            start_time = time.perf_counter()
            
            files = []
            page_token = None
            page_count = 0

            while True:
                page_count += 1
                logger.info(f"Fetching page {page_count} for query: {params.q}")
                
                results = self._service.files().list(
                    q=params.q,
                    pageSize=params.page_size,
                    orderBy=params.order_by,
                    pageToken=page_token,
                    fields=(
                        "nextPageToken,"
                        "files(id,name,mimeType,webViewLink,modifiedTime,size,ownedByMe,parents)"
                    )
                ).execute()

                raw_files = results.get("files", [])
                for f in raw_files:
                    files.append(
                        DriveFile(
                            id=f.get("id"),
                            name=f.get("name"),
                            mime_type=f.get("mimeType"),
                            web_view_link=f.get("webViewLink"),
                            modified_time=f.get("modifiedTime"),
                            size_bytes=int(f.get("size")) if f.get("size") else None,
                            owned_by_me=f.get("ownedByMe", False),
                            parent_folder_id=f.get("parents")[0] if f.get("parents") else None
                        )
                    )

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            duration = (time.perf_counter() - start_time) * 1000
            logger.info(f"Drive search complete. Retrieved {len(files)} files in {duration:.2f}ms across {page_count} pages.")

            return files

        except HttpError as e:

            logger.error(
                f"Drive API search failed: {e}"
            )

            return []

    # ────────────────────────────────────────────────────────────────

    async def get_recursive_folder_ids(
        self,
        root_id: str
    ) -> List[str]:
        """
        Recursively fetch ALL nested subfolders.
        """
        if not root_id:
            logger.info("No root folder ID provided. Skipping recursive traversal for whole drive search.")
            return []

        import time
        start_time = time.perf_counter()

        if root_id in self._recursive_folder_cache:
            ids, ts = self._recursive_folder_cache[root_id]
            if (datetime.now() - ts).total_seconds() < 300:
                logger.info(f"Cache HIT for recursive folders (root: {root_id}). Using {len(ids)} folders.")
                return ids

        logger.info(f"Cache MISS. Starting deep recursive BFS traversal from root: {root_id}")
        
        discovered = {root_id}
        # Queue stores (folder_id, depth)
        queue = [(root_id, 0)]
        max_depth = 0

        try:
            while queue:
                current_parent, depth = queue.pop(0)
                max_depth = max(max_depth, depth)
                
                page_token = None
                while True:
                    q = (
                        f"'{current_parent}' in parents "
                        "and mimeType = 'application/vnd.google-apps.folder' "
                        "and trashed = false"
                    )

                    results = self._service.files().list(
                        q=q,
                        pageToken=page_token,
                        pageSize=1000,
                        fields="nextPageToken, files(id, name)"
                    ).execute()

                    for f in results.get("files", []):
                        fid = f.get("id")
                        if fid and fid not in discovered:
                            discovered.add(fid)
                            queue.append((fid, depth + 1))
                            logger.info(f"[{depth+1}] Discovered subfolder: {f.get('name')} ({fid})")

                    page_token = results.get("nextPageToken")
                    if not page_token:
                        break

            ids = list(discovered)
            duration = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Recursive traversal COMPLETE. "
                f"Folders: {len(ids)}, Max Depth: {max_depth}, Duration: {duration:.2f}ms"
            )

            self._recursive_folder_cache[root_id] = (ids, datetime.now())
            return ids

        except HttpError as e:

            logger.error(
                f"Recursive traversal failed: {e}"
            )

            return [root_id]

    # ────────────────────────────────────────────────────────────────

    async def get_folder_id(
        self,
        folder_name: str
    ) -> Optional[str]:

        try:

            root_id = (
                settings.google_drive_root_folder_id
            )

            allowed_ids = []

            if root_id:

                allowed_ids = await self.get_recursive_folder_ids(
                    root_id
                )

            q = (
                f"name = '{folder_name}' "
                f"and mimeType = "
                f"'application/vnd.google-apps.folder' "
                f"and trashed = false"
            )

            results = self._service.files().list(
                q=q,
                fields="files(id,parents)"
            ).execute()

            files = results.get(
                "files",
                []
            )

            if not allowed_ids:

                return (
                    files[0].get("id")
                    if files
                    else None
                )

            for f in files:

                parents = f.get(
                    "parents",
                    []
                )

                if any(
                    p in allowed_ids
                    for p in parents
                ):

                    return f.get("id")

            return None

        except HttpError as e:

            logger.error(
                f"Folder lookup failed: {e}"
            )

            return None
