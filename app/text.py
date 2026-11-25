"""Text helpers shared by adapters and detectors."""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def strip_html(s: str | None, limit: int = 6000) -> str:
    if not s:
        return ""
    for _ in range(3):  # Greenhouse content arrives escaped two or three times
        u = html.unescape(s)
        if u == s:
            break
        s = u
    s = _TAG.sub(" ", s)
    s = html.unescape(s).replace("\u00a0", " ")
    s = _WS.sub(" ", s).strip()
    return s[:limit]


def to_iso(value) -> str | None:
    """Accept ISO strings, 'YYYY-MM-DD HH:MM:SS UTC', epoch seconds or epoch milliseconds."""
    if value in (None, "", 0):
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            v = float(value)
            if v > 1e12:
                v /= 1000.0
            return datetime.fromtimestamp(v, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        s = str(value).strip().replace(" UTC", "+00:00")
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        if " " in s and "T" not in s:
            s = s.replace(" ", "T", 1)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OverflowError, OSError):
        pass
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, IndexError):
        return None


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")
