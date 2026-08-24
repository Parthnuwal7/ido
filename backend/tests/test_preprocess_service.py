"""Tests for preprocess_service changes.

Two groups:
  1. Robustness fixes for timestamp handling, where a malformed value currently crashes
     the request instead of degrading.
  2. The dict-accepting entry points the HTML connector feeds, which let the connector
     skip a serialize/parse round-trip while leaving the string API untouched.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.preprocess_service import (  # noqa: E402
    convert_to_local_time,
    enrich_event_with_local_time,
    parse_timestamp,
    preprocess_search_entries,
    preprocess_search_history,
    preprocess_watch_entries,
    preprocess_watch_history,
)

TZ = "Asia/Kolkata"

WATCH_ENTRY = {
    "header": "YouTube",
    "title": "Watched Big Political Shift",
    "titleUrl": "https://www.youtube.com/watch?v=gZDzL1uyJdw",
    "subtitles": [{"name": "AstroKapoor", "url": "https://www.youtube.com/channel/UCp"}],
    "time": "2026-08-21T06:43:55Z",
}


# --- robustness ------------------------------------------------------------------

def test_convert_to_local_time_returns_a_dict_for_unknown_timezone():
    """Returning None here is what makes enrich crash downstream."""
    result = convert_to_local_time("2026-08-21T06:43:55Z", "Not/AZone")

    assert isinstance(result, dict)
    assert result["timestamp_local"] is None


def test_enrich_survives_unknown_timezone():
    event = enrich_event_with_local_time({"timestamp_utc": "2026-08-21T06:43:55Z"},
                                         "Not/AZone")

    assert event["timestamp_local"] is None
    assert event["hour_local"] is None


def test_enrich_survives_unparseable_timestamp():
    event = enrich_event_with_local_time({"timestamp_utc": "garbage"}, TZ)

    assert event["timestamp_local"] is None


def test_parse_timestamp_returns_none_for_unparseable_input():
    """Echoing the input back disguises a failure as a value."""
    assert parse_timestamp("garbage") is None


def test_parse_timestamp_normalises_offset_form_to_utc():
    assert parse_timestamp("2026-08-21T12:13:55+05:30") == "2026-08-21T06:43:55Z"


def test_parse_timestamp_still_handles_the_json_export_forms():
    assert parse_timestamp("2026-08-21T06:43:55Z") == "2026-08-21T06:43:55Z"
    assert parse_timestamp("2026-08-21T06:43:55.123000Z") == "2026-08-21T06:43:55.123000Z"


# --- dict entry points -----------------------------------------------------------

def test_preprocess_watch_entries_accepts_dicts():
    (event,) = preprocess_watch_entries([WATCH_ENTRY], TZ)

    assert event["type"] == "watch"
    assert event["channel"] == "AstroKapoor"
    assert event["timestamp_utc"] == "2026-08-21T06:43:55Z"
    assert event["hour_local"] == 12


def test_watch_entries_and_watch_history_agree():
    """The string API must stay a thin wrapper, not a second implementation."""
    from_dicts = preprocess_watch_entries([WATCH_ENTRY], TZ)
    from_string = preprocess_watch_history(json.dumps([WATCH_ENTRY]), TZ)

    assert from_dicts == from_string


def test_preprocess_watch_history_string_api_unchanged():
    events = preprocess_watch_history(json.dumps([WATCH_ENTRY]), TZ)

    assert len(events) == 1
    assert events[0]["type"] == "watch"


def test_preprocess_watch_history_still_tolerates_bad_json():
    assert preprocess_watch_history("not json", TZ) == []


def test_search_entries_and_search_history_agree():
    entry = {
        "header": "YouTube",
        "title": "Searched for phasor diagram",
        "titleUrl": "https://www.youtube.com/results?search_query=phasor",
        "time": "2026-08-21T06:43:55Z",
    }

    assert preprocess_search_entries([entry], TZ) == preprocess_search_history(
        json.dumps([entry]), TZ
    )


def test_ads_are_still_dropped_through_the_dict_path():
    ad = {**WATCH_ENTRY, "details": [{"name": "From Google Ads"}]}

    assert preprocess_watch_entries([ad], TZ) == []


def test_posts_are_still_dropped_through_the_dict_path():
    post = {**WATCH_ENTRY, "titleUrl": "https://www.youtube.com/post/Ugkx748"}

    assert preprocess_watch_entries([post], TZ) == []
