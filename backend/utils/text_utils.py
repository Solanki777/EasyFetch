"""String normalisation utilities for search and deduplication."""
from __future__ import annotations

import re
import unicodedata


def normalise(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def escape_drive_string(value: str) -> str:
    """
    Escape a user-provided string for safe use inside a Drive API q string.
    Drive requires single quotes to be escaped with a backslash.
    """
    return value.replace("\\", "\\\\").replace("'", "\\'")


def get_name_stem(filename: str) -> str:
    """
    Extract the base stem of a filename for similarity comparison.
    Removes:
      - file extension
      - common version suffixes (v1, v2, final, draft, copy, backup)
      - leading/trailing noise
    """
    stem = filename.lower()
    # Remove extension
    stem = re.sub(r"\.\w{1,6}$", "", stem)
    # Remove version/draft markers
    stem = re.sub(
        r"[\s_\-]*(v\d+(\.\d+)?|final|draft|copy|backup|rev|revision|old|new|updated?)[\s_\-]*",
        "",
        stem,
        flags=re.IGNORECASE,
    )
    # Collapse whitespace and separators
    stem = re.sub(r"[\s_\-]+", " ", stem).strip()
    return stem


def tokenise(text: str) -> list[str]:
    """Split text into lowercase word tokens."""
    return re.findall(r"\b\w+\b", text.lower())


def contains_all_tokens(haystack: str, query: str) -> bool:
    """Return True if every token from query appears in haystack."""
    hay_tokens = set(tokenise(haystack))
    return all(t in hay_tokens for t in tokenise(query))
