"""
Google Drive API client service.
"""
from __future__ import annotations

import logging
from typing import List, Optional

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
            print("\n===== DRIVE QUERY =====")
            print(params.q)

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

    async def get_folder_id(self, folder_name: str) -> Optional[str]:
        """
        Get Google Drive folder ID by folder name.
        """

        if not self._service:
            return None

        try:
            q = (
                f"name = '{folder_name}' "
                f"and mimeType = "
                f"'application/vnd.google-apps.folder' "
                f"and trashed = false"
            )

            results = self._service.files().list(
                q=q,
                fields="files(id)"
            ).execute()

            files = results.get("files", [])

            return files[0].get("id") if files else None

        except HttpError as e:
            logger.error("Folder lookup failed: %s", e)

