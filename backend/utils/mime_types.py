"""
MIME type registry for Google Drive query building.

Two-way lookup:
  extension → MIME type   (used by QueryBuilder)
  MIME type → display name (used by ranking, response formatter, UI)
"""
from __future__ import annotations

EXTENSION_TO_MIME: dict[str, str] = {
    # Documents
    "pdf":   "application/pdf",
    "doc":   "application/msword",
    "docx":  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "odt":   "application/vnd.oasis.opendocument.text",
    "rtf":   "application/rtf",
    "txt":   "text/plain",
    # Spreadsheets
    "xls":   "application/vnd.ms-excel",
    "xlsx":  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv":   "text/csv",
    "ods":   "application/vnd.oasis.opendocument.spreadsheet",
    # Presentations
    "ppt":   "application/vnd.ms-powerpoint",
    "pptx":  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "odp":   "application/vnd.oasis.opendocument.presentation",
    # Images
    "png":   "image/png",
    "jpg":   "image/jpeg",
    "jpeg":  "image/jpeg",
    "gif":   "image/gif",
    "svg":   "image/svg+xml",
    "webp":  "image/webp",
    # Video / Audio
    "mp4":   "video/mp4",
    "mov":   "video/quicktime",
    "mp3":   "audio/mpeg",
    # Archives
    "zip":   "application/zip",
    "tar":   "application/x-tar",
    # Code
    "json":  "application/json",
    "xml":   "application/xml",
    "html":  "text/html",
    "py":    "text/x-python",
    # Google Workspace native types
    "gdoc":   "application/vnd.google-apps.document",
    "gsheet": "application/vnd.google-apps.spreadsheet",
    "gslide": "application/vnd.google-apps.presentation",
    "gform":  "application/vnd.google-apps.form",
    "gdraw":  "application/vnd.google-apps.drawing",
    "gsite":  "application/vnd.google-apps.site",
}

# Reverse lookup: MIME → human-readable display name
MIME_DISPLAY_NAMES: dict[str, str] = {
    mime: ext.upper() for ext, mime in EXTENSION_TO_MIME.items()
}

# Human-friendly labels for common MIME types
MIME_LABELS: dict[str, str] = {
    "application/pdf": "PDF",
    "application/msword": "Word Doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PowerPoint",
    "text/plain": "Text",
    "text/csv": "CSV",
    "image/png": "PNG Image",
    "image/jpeg": "JPEG Image",
    "video/mp4": "MP4 Video",
    "application/vnd.google-apps.document": "Google Doc",
    "application/vnd.google-apps.spreadsheet": "Google Sheet",
    "application/vnd.google-apps.presentation": "Google Slide",
    "application/vnd.google-apps.form": "Google Form",
    "application/vnd.google-apps.folder": "Folder",
}


def get_mime_label(mime_type: str) -> str:
    """Return a human-readable label for a MIME type."""
    return MIME_LABELS.get(mime_type, MIME_DISPLAY_NAMES.get(mime_type, mime_type.split("/")[-1].upper()))


def extension_to_mime(ext: str) -> str | None:
    """Resolve a file extension to its MIME type."""
    return EXTENSION_TO_MIME.get(ext.lower().lstrip("."))


def extensions_to_mimes(extensions: list[str]) -> list[str]:
    """Resolve a list of extensions to unique MIME types, dropping unknowns."""
    seen: set[str] = set()
    result: list[str] = []
    for ext in extensions:
        mime = extension_to_mime(ext)
        if mime and mime not in seen:
            seen.add(mime)
            result.append(mime)
    return result
