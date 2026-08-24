"""
Choosing and applying the Wrapped's calendar year.

A Wrapped covers one year, but a Takeout export spans everything YouTube still retains
-- the reference export holds 2025 and 2026 watch history alongside 2020-2022 searches.
Without this, every card summarises all-time data under a current-year label.

Filtering happens on Takeout JSON entries, before preprocessing, so the expensive work
(text cleaning, language detection, timezone enrichment) only runs on the entries that
will actually reach a card.

Year boundaries are local, not UTC. A video watched at 02:00 on Jan 1 in Kolkata is
20:30 on Dec 31 in UTC; from the viewer's perspective it belongs to the new year.
"""

from collections import OrderedDict
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import pytz


def _resolve(timezone: str):
    try:
        return pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        return pytz.UTC


def _year_in(time_str: Optional[str], tz) -> Optional[int]:
    """Year of a UTC timestamp in an already-resolved timezone."""
    if not time_str:
        return None

    try:
        moment = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None

    if moment.tzinfo is None:
        moment = pytz.UTC.localize(moment)

    return moment.astimezone(tz).year


def local_year(time_str: Optional[str], timezone: str) -> Optional[int]:
    """Calendar year of a UTC timestamp as seen in `timezone`, or None if unreadable."""
    return _year_in(time_str, _resolve(timezone))


def partition_by_year(entries: Iterable[Dict], timezone: str) -> Dict[Optional[int], List[Dict]]:
    """Group Takeout entries by local calendar year, preserving order within each year.

    Entries with no readable timestamp land under None. Subscriptions never reach here
    -- subscriptions.csv carries no date column, so they are exempt from year filtering
    entirely and pass straight through the ingest.

    The timezone is resolved once rather than per entry: at 42,500 entries that lookup
    is the difference between ~30 us and ~5 us each.
    """
    tz = _resolve(timezone)
    buckets: Dict[Optional[int], List[Dict]] = OrderedDict()

    for item in entries:
        buckets.setdefault(_year_in(item.get("time"), tz), []).append(item)

    return buckets


def select_year(
    available: Iterable[Optional[int]],
    requested: Optional[int] = None,
    today_year: Optional[int] = None,
) -> Optional[int]:
    """Decide which year the Wrapped covers.

    An explicit request always wins, even when that year holds no data -- the caller
    reports "no data for that year" rather than silently substituting a different one.
    Otherwise the current year is used when it has data, falling back to the most recent
    year that does. That fallback is what stops a January upload, or an export whose
    newest history predates this year, from producing an empty Wrapped.
    """
    if requested is not None:
        return requested

    years = sorted(y for y in available if y is not None)
    if not years:
        return None

    current = today_year if today_year is not None else datetime.now().year
    return current if current in years else years[-1]
