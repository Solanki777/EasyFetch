"""
Universal MIME type registry for intelligent Google Drive discovery.
"""
from __future__ import annotations

# Extension → MIME Type
EXTENSION_TO_MIME: dict[str, str] = {
    # Documents
    "pdf":   "application/pdf",
    "doc":   "application/msword",
    "docx":  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "odt":   "application/vnd.oasis.opendocument.text",
    "rtf":   "application/rtf",
    "txt":   "text/plain",
    "gdoc":  "application/vnd.google-apps.document",

    # Spreadsheets
    "xls":   "application/vnd.ms-excel",
    "xlsx":  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv":   "text/csv",
    "gsheet": "application/vnd.google-apps.spreadsheet",

    # Presentations
    "ppt":   "application/vnd.ms-powerpoint",
    "pptx":  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "gslide": "application/vnd.google-apps.presentation",

    # Images
    "png":   "image/png",
    "jpg":   "image/jpeg",
    "jpeg":  "image/jpeg",
    "gif":   "image/gif",
    "svg":   "image/svg+xml",
    "webp":  "image/webp",

    # Video
    "mp4":   "video/mp4",
    "mkv":   "video/x-matroska",
    "mov":   "video/quicktime",
    "avi":   "video/x-msvideo",

    # Audio
    "mp3":   "audio/mpeg",
    "wav":   "audio/wav",
    "flac":  "audio/flac",

    # Archives
    "zip":   "application/zip",
    "rar":   "application/x-rar-compressed",
    "tar":   "application/x-tar",
    "7z":    "application/x-7z-compressed",

    # Code
    "py":    "text/x-python",
    "js":    "text/javascript",
    "ts":    "text/typescript",
    "java":  "text/x-java-source",
    "cpp":   "text/x-c++src",
    "html":  "text/html",
    "css":   "text/css",
    "json":  "application/json",
}

# Category → MIME Types
CATEGORY_TO_MIMES: dict[str, list[str]] = {
    "images": ["image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"],
    "documents": [
        "application/pdf", 
        "application/vnd.google-apps.document",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "application/rtf"
    ],
    "spreadsheets": [
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv"
    ],
    "presentations": [
        "application/vnd.google-apps.presentation",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint"
    ],
    "archives": [
        "application/zip",
        "application/x-rar-compressed",
        "application/x-tar",
        "application/x-7z-compressed"
    ],
    "code": [
        "text/x-python", "text/javascript", "text/typescript", 
        "text/x-java-source", "text/x-c++src", "text/html", 
        "text/css", "application/json"
    ],
    "video": ["video/mp4", "video/x-matroska", "video/quicktime", "video/x-msvideo"],
    "audio": ["audio/mpeg", "audio/wav", "audio/flac"],
    "folders": ["application/vnd.google-apps.folder"],
}

# Alias mapping for NL understanding
MIME_ALIASES: dict[str, str] = {
    "excel": "spreadsheets",
    "sheets": "spreadsheets",
    "word": "documents",
    "docs": "documents",
    "powerpoint": "presentations",
    "slides": "presentations",
    "pictures": "images",
    "photos": "images",
    "zips": "archives",
    "scripts": "code",
    "programming": "code",
    "movies": "video",
    "music": "audio",
}

MIME_LABELS: dict[str, str] = {
    "application/pdf": "PDF Document",
    "application/vnd.google-apps.document": "Google Doc",
    "application/vnd.google-apps.spreadsheet": "Google Sheet",
    "application/vnd.google-apps.presentation": "Google Slide",
    "application/vnd.google-apps.folder": "Folder",
    "application/zip": "Archive",
    "image/jpeg": "Image",
    "image/png": "Image",
    "video/mp4": "Video",
    "text/plain": "Text File",
    "text/x-python": "Python Script",
}

def get_mimes_for_query(term: str) -> list[str]:
    """Resolve a natural language term or extension to a list of MIME types."""
    term = term.lower().strip()
    
    # 1. Check direct category
    if term in CATEGORY_TO_MIMES:
        return CATEGORY_TO_MIMES[term]
        
    # 2. Check alias
    if term in MIME_ALIASES:
        return CATEGORY_TO_MIMES[MIME_ALIASES[term]]
        
    # 3. Check extension
    ext = term.lstrip(".")
    if ext in EXTENSION_TO_MIME:
        return [EXTENSION_TO_MIME[ext]]
        
    return []

def get_mime_label(mime_type: str) -> str:
    """Return a human-readable label."""
    if mime_type in MIME_LABELS:
        return MIME_LABELS[mime_type]
    return mime_type.split("/")[-1].upper()
