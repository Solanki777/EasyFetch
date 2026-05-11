"""Date parsing and resolution utilities."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

from dateutil.relativedelta import relativedelta


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def resolve_relative_date(relative: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Convert a relative date keyword into an (after, before) UTC datetime tuple.

    Returns:
        (after, before) — either may be None if not applicable.
    """
    now = now_utc()

    mapping = {
        "today":      (now.replace(hour=0, minute=0, second=0, microsecond=0), now),
        "this_week":  (now - relativedelta(weeks=1), now),
        "this_month": (now - relativedelta(months=1), now),
        "this_year":  (now - relativedelta(years=1), now),
    }

    return mapping.get(relative, (None, None))


def format_drive_datetime(dt: datetime) -> str:
    """Format a datetime object as an RFC 3339 string for Drive API queries."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 / RFC 3339 string to a UTC-aware datetime."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def human_relative(dt: Optional[datetime]) -> str:
    """Return a human-friendly relative time string."""
    if not dt:
        return "unknown"
    now = now_utc()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    days = delta.days

    if days == 0:
        return "today"
    elif days == 1:
        return "yesterday"
    elif days < 7:
        return f"{days} days ago"
    elif days < 30:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif days < 365:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
