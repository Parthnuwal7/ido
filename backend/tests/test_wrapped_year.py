"""Tests for wrapped_year: choosing and applying the Wrapped's calendar year.

Year boundaries are local, not UTC: a video watched at 02:00 on Jan 1 in Kolkata is
still 20:30 on Dec 31 in UTC, and belongs to the new year from the viewer's perspective.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.wrapped_year import (  # noqa: E402
    local_year,
    partition_by_year,
    select_year,
)

IST = "Asia/Kolkata"
NY = "America/New_York"


def entry(time_str, title="Watched X"):
    return {"title": title, "titleUrl": "https://y/watch?v=1", "time": time_str}


# --- local_year ------------------------------------------------------------------

def test_local_year_uses_local_boundary_not_utc():
    """20:30 Dec 31 UTC is 02:00 Jan 1 in Kolkata -- the new year."""
    assert local_year("2025-12-31T20:30:00Z", IST) == 2026


def test_local_year_rolls_backwards_for_western_zones():
    """00:30 Jan 1 UTC is still 19:30 Dec 31 in New York -- the old year."""
    assert local_year("2026-01-01T00:30:00Z", NY) == 2025


def test_local_year_handles_microsecond_form():
    assert local_year("2026-08-21T06:43:55.123000Z", IST) == 2026


def test_local_year_is_none_for_missing_or_bad_time():
    assert local_year(None, IST) is None
    assert local_year("", IST) is None
    assert local_year("garbage", IST) is None


# --- partition_by_year -----------------------------------------------------------

def test_partition_groups_entries_by_local_year():
    entries = [
        entry("2026-08-21T06:43:55Z"),
        entry("2026-01-02T06:43:55Z"),
        entry("2025-06-01T06:43:55Z"),
    ]

    buckets = partition_by_year(entries, IST)

    assert sorted(buckets) == [2025, 2026]
    assert len(buckets[2026]) == 2
    assert len(buckets[2025]) == 1


def test_partition_puts_undated_entries_under_none():
    buckets = partition_by_year([entry(None), entry("2026-08-21T06:43:55Z")], IST)

    assert len(buckets[None]) == 1
    assert len(buckets[2026]) == 1


def test_partition_preserves_order_within_a_year():
    entries = [entry("2026-01-01T06:00:00Z", "A"), entry("2026-01-02T06:00:00Z", "B")]

    assert [e["title"] for e in partition_by_year(entries, IST)[2026]] == ["A", "B"]


def test_partition_of_nothing_is_empty():
    assert partition_by_year([], IST) == {}


# --- select_year -----------------------------------------------------------------

def test_requested_year_wins_when_available():
    assert select_year([2024, 2025, 2026], requested=2025, today_year=2026) == 2025


def test_requested_year_is_returned_even_when_it_has_no_data():
    """The caller reports 'no data for that year' rather than silently substituting."""
    assert select_year([2025, 2026], requested=2024, today_year=2026) == 2024


def test_defaults_to_current_year_when_it_has_data():
    assert select_year([2025, 2026], requested=None, today_year=2026) == 2026


def test_falls_back_to_most_recent_year_with_data():
    """A January upload, or a stale export, must not produce an empty Wrapped."""
    assert select_year([2023, 2025], requested=None, today_year=2026) == 2025


def test_returns_none_when_no_years_have_data():
    assert select_year([], requested=None, today_year=2026) is None


def test_ignores_the_undated_bucket_when_choosing():
    assert select_year([None, 2025], requested=None, today_year=2026) == 2025
