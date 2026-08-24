"""
Locating history members inside a Takeout ZIP.

Single source of truth for which member holds which history, and in which format.
Google Takeout exports history as HTML by default -- JSON requires the user to open
"Multiple formats" and switch it -- so both formats have to be found, with JSON
preferred because it is lossless and carries no parsing risk.

Replaces the inline discovery loop in wrapped_routes.py and TARGET_FILES in
zip_service.py, which previously each hard-coded a JSON-only lookup.
"""

from dataclasses import dataclass
from typing import List, Optional

JSON = "json"
HTML = "html"

# JSON first: preference is by basename order here, never by ZIP entry order.
_WATCH = ("watch-history.json", "watch-history.html")
_SEARCH = ("search-history.json", "search-history.html")
_SUBSCRIPTIONS = "subscriptions.csv"


@dataclass(frozen=True)
class HistoryFile:
    """A located ZIP member and the format its contents are in."""

    member: str
    format: str


@dataclass(frozen=True)
class HistoryFiles:
    watch: Optional[HistoryFile] = None
    search: Optional[HistoryFile] = None
    subscriptions: Optional[str] = None


def _find(namelist: List[str], basename: str) -> Optional[str]:
    """First member whose basename matches, at any directory depth."""
    target = basename.lower()
    for member in namelist:
        if member.split("/")[-1].lower() == target:
            return member
    return None


def _first_available(namelist: List[str], candidates) -> Optional[HistoryFile]:
    """Try candidates in preference order, not in ZIP order."""
    for basename in candidates:
        member = _find(namelist, basename)
        if member:
            return HistoryFile(member=member, format=basename.rsplit(".", 1)[1])
    return None


def find_history(namelist: List[str]) -> HistoryFiles:
    """Locate watch history, search history and subscriptions in a ZIP namelist."""
    return HistoryFiles(
        watch=_first_available(namelist, _WATCH),
        search=_first_available(namelist, _SEARCH),
        subscriptions=_find(namelist, _SUBSCRIPTIONS),
    )
