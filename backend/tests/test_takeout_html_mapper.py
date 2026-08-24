"""Tests for takeout_html_mapper: raw cells -> Takeout JSON entry dicts.

The mapper's contract is fidelity: emit what Google's JSON export would have contained,
so preprocess_watch_history and its is_google_ads / is_youtube_post filters run unchanged.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.takeout_html_mapper import (  # noqa: E402
    to_search_entries,
    to_watch_entries,
)
from services.takeout_time import BAD_FORMAT, TZ_MISMATCH  # noqa: E402

TZ = "Asia/Kolkata"
STAMP = "Aug 21, 2026, 12:13:55 PM IST"
UTC_STAMP = "2026-08-21T06:43:55Z"

VIDEO = "https://www.youtube.com/watch?v=gZDzL1uyJdw"
CHANNEL = "https://www.youtube.com/channel/UCpg-rSVxo3EgwEmWHl2nN9A"


def raw(prefix="Watched", links=(), product="YouTube", timestamp=STAMP, is_ad=False):
    return {
        "product": product,
        "prefix": prefix,
        "links": list(links),
        "timestamp": timestamp,
        "is_ad": is_ad,
    }


def test_normal_video_maps_to_full_entry():
    cells = [raw(links=[(VIDEO, "Big Political Shift"), (CHANNEL, "AstroKapoor")])]

    entries, _ = to_watch_entries(cells, TZ)

    assert entries == [
        {
            "header": "YouTube",
            "title": "Watched Big Political Shift",
            "titleUrl": VIDEO,
            "subtitles": [{"name": "AstroKapoor", "url": CHANNEL}],
            "time": UTC_STAMP,
        }
    ]


def test_private_video_has_no_subtitles_key():
    """Google renders the raw URL as anchor text when it cannot resolve a title."""
    cells = [raw(links=[(VIDEO, VIDEO)])]

    (entry,), _ = to_watch_entries(cells, TZ)

    assert entry["title"] == f"Watched {VIDEO}"
    assert "subtitles" not in entry


def test_ad_carries_details_so_is_google_ads_still_fires():
    cells = [raw(links=[(VIDEO, "Some Ad")], is_ad=True)]

    (entry,), _ = to_watch_entries(cells, TZ)

    assert entry["details"] == [{"name": "From Google Ads"}]


def test_non_ad_has_no_details_key():
    cells = [raw(links=[(VIDEO, "Title"), (CHANNEL, "Chan")])]

    (entry,), _ = to_watch_entries(cells, TZ)

    assert "details" not in entry


def test_post_keeps_its_url_so_is_youtube_post_still_fires():
    """5,010 of 5,214 posts carry a channel link, so link count cannot identify them."""
    post = "https://www.youtube.com/post/Ugkx748uDlJQ"
    cells = [raw(prefix="Viewed", links=[(post, "thoughts"), (CHANNEL, "Dapo")])]

    (entry,), _ = to_watch_entries(cells, TZ)

    assert entry["titleUrl"] == post


def test_music_entry_keeps_product_and_music_host():
    music = "https://music.youtube.com/watch?v=Zsd4TyucE40"
    cells = [raw(links=[(music, "remember to rest"), (CHANNEL, "Artist - Topic")],
                 product="YouTube Music")]

    (entry,), _ = to_watch_entries(cells, TZ)

    assert entry["header"] == "YouTube Music"
    assert entry["titleUrl"] == music


def test_link_less_activity_has_no_title_url():
    cells = [raw(prefix="Viewed a post that is no longer available")]

    (entry,), _ = to_watch_entries(cells, TZ)

    assert entry["title"] == "Viewed a post that is no longer available"
    assert "titleUrl" not in entry


def test_unparseable_timestamp_drops_entry_and_counts_it():
    cells = [
        raw(links=[(VIDEO, "Good")], timestamp=STAMP),
        raw(links=[(VIDEO, "Bad")], timestamp="21/08/2026 12:13:55 IST"),
    ]

    entries, report = to_watch_entries(cells, TZ)

    assert len(entries) == 1
    assert report["cells_seen"] == 2
    assert report["entries_emitted"] == 1
    assert report["dropped"][BAD_FORMAT] == 1


def test_timezone_mismatch_is_warned_not_dropped():
    cells = [raw(links=[(VIDEO, "Title")])]

    entries, report = to_watch_entries(cells, "America/New_York")

    assert len(entries) == 1
    assert report["warnings"][TZ_MISMATCH] == 1


def test_report_is_empty_for_a_clean_run():
    cells = [raw(links=[(VIDEO, "Title"), (CHANNEL, "Chan")])]

    _, report = to_watch_entries(cells, TZ)

    assert report["dropped"] == {}
    assert report["warnings"] == {}


def test_search_entry_shape():
    query = "https://www.youtube.com/results?search_query=phasor+diagram"
    cells = [raw(prefix="Searched for", links=[(query, "phasor diagram")])]

    entries, _ = to_search_entries(cells, TZ)

    assert entries == [
        {
            "header": "YouTube",
            "title": "Searched for phasor diagram",
            "titleUrl": query,
            "time": UTC_STAMP,
        }
    ]


def test_search_entries_feed_the_existing_preprocessor():
    """End-to-end shape check: the real preprocessor must recover the query text."""
    import json

    from services.preprocess_service import preprocess_search_history

    query = "https://www.youtube.com/results?search_query=phasor+diagram"
    cells = [raw(prefix="Searched for", links=[(query, "phasor diagram")])]
    entries, _ = to_search_entries(cells, TZ)

    (event,) = preprocess_search_history(json.dumps(entries), TZ)

    assert event["type"] == "search"
    assert event["text_raw"] == "phasor diagram"
    assert event["timestamp_utc"] == UTC_STAMP
