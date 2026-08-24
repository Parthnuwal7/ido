"""Tests for takeout_time: Takeout HTML wall-clock strings -> UTC instants."""
import os
import sys
from datetime import datetime

import pytest
import pytz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.takeout_time import (  # noqa: E402
    BAD_FORMAT,
    NONEXISTENT,
    TZ_MISMATCH,
    UNKNOWN_TZ,
    to_utc,
)

UTC = pytz.UTC


def test_parses_en_us_wall_clock_with_narrow_nbsp():
    """Takeout separates seconds from AM/PM with U+202F, which strptime rejects."""
    result = to_utc("Aug 21, 2026, 12:13:55 PM IST", "Asia/Kolkata")

    assert result.reason is None
    assert result.utc == datetime(2026, 8, 21, 6, 43, 55, tzinfo=UTC)


@pytest.mark.parametrize("sep", [" ", " ", " "])
def test_accepts_all_space_variants_before_meridiem(sep):
    result = to_utc(f"Aug 21, 2026, 12:13:55{sep}PM IST", "Asia/Kolkata")

    assert result.reason is None
    assert result.utc == datetime(2026, 8, 21, 6, 43, 55, tzinfo=UTC)


def test_no_double_shift_round_trip():
    """The +5:30 wall clock must come back as the same wall clock, not shifted twice."""
    tz = pytz.timezone("Asia/Kolkata")

    result = to_utc("Aug 21, 2026, 12:13:55 PM IST", "Asia/Kolkata")
    back = result.utc.astimezone(tz)

    assert (back.hour, back.minute, back.second) == (12, 13, 55)


def test_unrecognised_format_reports_bad_format():
    result = to_utc("21/08/2026 12:13:55 IST", "Asia/Kolkata")

    assert result.utc is None
    assert result.reason == BAD_FORMAT


def test_missing_abbreviation_reports_bad_format():
    result = to_utc("Aug 21, 2026, 12:13:55 PM", "Asia/Kolkata")

    assert result.utc is None
    assert result.reason == BAD_FORMAT


def test_ambiguous_dst_hour_resolved_by_abbreviation():
    """01:30 on 2026-11-01 happens twice in New York. EDT and EST are different instants."""
    edt = to_utc("Nov 1, 2026, 1:30:00 AM EDT", "America/New_York")
    est = to_utc("Nov 1, 2026, 1:30:00 AM EST", "America/New_York")

    assert edt.reason is None and est.reason is None
    assert edt.utc == datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
    assert est.utc == datetime(2026, 11, 1, 6, 30, tzinfo=UTC)
    assert est.utc != edt.utc


def test_nonexistent_dst_hour_is_reported_not_guessed():
    """02:30 on 2026-03-08 never happened in New York."""
    result = to_utc("Mar 8, 2026, 2:30:00 AM EST", "America/New_York")

    assert result.utc is None
    assert result.reason == NONEXISTENT


def test_abbreviation_mismatch_falls_back_to_table_and_warns():
    """Exported in India, viewing as New York: IST must still resolve to +05:30."""
    result = to_utc("Aug 21, 2026, 12:13:55 PM IST", "America/New_York")

    assert result.reason is None
    assert result.utc == datetime(2026, 8, 21, 6, 43, 55, tzinfo=UTC)
    assert result.warning == TZ_MISMATCH


def test_unresolvable_abbreviation_reports_unknown_tz():
    result = to_utc("Aug 21, 2026, 12:13:55 PM ZZZ", "America/New_York")

    assert result.utc is None
    assert result.reason == UNKNOWN_TZ


def test_matching_abbreviation_emits_no_warning():
    result = to_utc("Aug 21, 2026, 12:13:55 PM IST", "Asia/Kolkata")

    assert result.warning is None


def test_blank_input_reports_bad_format():
    assert to_utc("", "Asia/Kolkata").reason == BAD_FORMAT
    assert to_utc(None, "Asia/Kolkata").reason == BAD_FORMAT
