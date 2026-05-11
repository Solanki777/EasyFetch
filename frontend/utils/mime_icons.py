"""MIME type → emoji icon mapping for the result card UI."""
from __future__ import annotations

MIME_ICONS: dict[str, str] = {
    "application/pdf":                                                               "📄",
    "application/msword":                                                            "📝",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":      "📝",
    "application/vnd.ms-excel":                                                     "📊",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":            "📊",
    "text/csv":                                                                      "📊",
    "application/vnd.ms-powerpoint":                                                "📐",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation":    "📐",
    "text/plain":                                                                    "📃",
    "application/zip":                                                               "🗜️",
    "image/png":                                                                     "🖼️",
    "image/jpeg":                                                                    "🖼️",
    "image/gif":                                                                     "🖼️",
    "image/svg+xml":                                                                 "🖼️",
    "video/mp4":                                                                     "🎬",
    "video/quicktime":                                                               "🎬",
    "audio/mpeg":                                                                    "🎵",
    "application/vnd.google-apps.document":                                          "📝",
    "application/vnd.google-apps.spreadsheet":                                      "📊",
    "application/vnd.google-apps.presentation":                                      "📐",
    "application/vnd.google-apps.form":                                              "📋",
    "application/vnd.google-apps.drawing":                                           "🎨",
    "application/vnd.google-apps.folder":                                            "📂",
}

DEFAULT_ICON = "📁"


def get_mime_icon(mime_type: str) -> str:
    return MIME_ICONS.get(mime_type, DEFAULT_ICON)
