"""Tests for history_locator: finding history members inside a Takeout ZIP.

Single source of truth, replacing the duplicated discovery in wrapped_routes.py and
zip_service.py which today carry the same JSON-only assumption independently.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.history_locator import HTML, JSON, find_history  # noqa: E402

BASE = "Takeout/YouTube and YouTube Music"
WATCH_HTML = f"{BASE}/history/watch-history.html"
WATCH_JSON = f"{BASE}/history/watch-history.json"
SEARCH_HTML = f"{BASE}/history/search-history.html"
SUBS = f"{BASE}/subscriptions/subscriptions.csv"


def test_finds_html_watch_history():
    found = find_history([WATCH_HTML, SUBS])

    assert found.watch.member == WATCH_HTML
    assert found.watch.format == HTML


def test_prefers_json_over_html_when_both_present():
    """JSON is lossless and parse-risk-free, so it wins whenever available."""
    found = find_history([WATCH_HTML, WATCH_JSON])

    assert found.watch.member == WATCH_JSON
    assert found.watch.format == JSON


def test_json_preference_is_independent_of_zip_entry_order():
    forward = find_history([WATCH_JSON, WATCH_HTML])
    reverse = find_history([WATCH_HTML, WATCH_JSON])

    assert forward.watch.member == reverse.watch.member == WATCH_JSON


def test_finds_search_history_and_subscriptions():
    found = find_history([WATCH_HTML, SEARCH_HTML, SUBS])

    assert found.search.member == SEARCH_HTML
    assert found.search.format == HTML
    assert found.subscriptions == SUBS


def test_missing_members_are_none():
    found = find_history([SUBS])

    assert found.watch is None
    assert found.search is None


def test_empty_namelist_finds_nothing():
    found = find_history([])

    assert found.watch is None
    assert found.search is None
    assert found.subscriptions is None


def test_matches_regardless_of_directory_depth():
    deep = f"some/other/prefix/{WATCH_HTML}"

    assert find_history([deep]).watch.member == deep


def test_basename_match_is_case_insensitive():
    found = find_history([f"{BASE}/history/Watch-History.HTML"])

    assert found.watch is not None
    assert found.watch.format == HTML


def test_ignores_unrelated_members():
    found = find_history(
        [f"{BASE}/playlists/watch-history-notes.txt", f"{BASE}/videos/clip.mp4"]
    )

    assert found.watch is None
