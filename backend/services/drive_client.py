"""
Google Drive API client service.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

from google.oauth2 import service_account
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
        self._service = build("drive", "v3", credentials=self._creds)

    def _load_credentials(self):
        cred_path = "credentials/service_account.json"
        if not os.path.exists(cred_path):
            logger.warning("Credentials file missing at %s", cred_path)
            return None
        return service_account.Credentials.from_service_account_file(
            cred_path,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )

    async def search(self, params: DriveSearchParams) -> List[DriveFile]:
        if not self._service: return []
        try:
            results = self._service.files().list(
                q=params.q,
                orderBy=params.order_by,
                pageSize=params.page_size,
                fields="files(id, name, mimeType, webViewLink, modifiedTime, size, owners, ownedByMe, parents)",
                supportsAllDrives=params.supports_all_drives,
                includeItemsFromAllDrives=params.include_items_from_all_drives,
                driveId=params.drive_id,
                corpora=params.corpora
            ).execute()

            files = []
            for f in results.get("files", []):
                files.append(DriveFile(
                    id=f.get("id"),
                    name=f.get("name"),
                    mime_type=f.get("mimeType"),
                    web_view_link=f.get("webViewLink"),
                    modified_time=f.get("modifiedTime"),
                    size_bytes=int(f.get("size")) if f.get("size") else None,
                    owned_by_me=f.get("ownedByMe", False),
                    parent_folder_id=f.get("parents")[0] if f.get("parents") else None
                ))
            return files
        except HttpError as e:
            logger.error("Drive API error: %s", e)
            return []

    async def get_folder_id(self, folder_name: str) -> Optional[str]:
        if not self._service: return None
        try:
            q = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self._service.files().list(q=q, fields="files(id)").execute()
            files = results.get("files", [])
            return files[0].get("id") if files else None
        except HttpError:
            return None
