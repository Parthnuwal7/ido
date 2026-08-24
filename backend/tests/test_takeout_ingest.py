"""Tests for takeout_ingest: a Takeout ZIP -> events, stats and a parse report.

This is the logic that used to live inline in wrapped_routes.process_zip_in_memory.
Extracting it keeps the route thin and lets the ingest path be tested without FastAPI.
"""
import io
import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.takeout_ingest import (  # noqa: E402
    MIN_YIELD,
    HistoryParseError,
    ingest_zip,
)

TZ = "Asia/Kolkata"
BASE = "Takeout/YouTube and YouTube Music"
NBSP, NNBSP = "\xa0", " "

CAPTION = "<b>Products:</b><br>&emsp;YouTube<br><b>Why is this here?</b><br>&emsp;x"


def cell(body, product="YouTube", caption=CAPTION):
    return (
        '<div class="outer-cell mdl-cell"><div class="mdl-grid">'
        '<div class="header-cell mdl-cell mdl-cell--12-col">'
        f'<p class="mdl-typography--title">{product}<br></p></div>'
        '<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">'
        f"{body}</div>"
        '<div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">'
        f"{caption}</div></div></div>"
    )


def watch_cell(title="A Video", stamp=f"Aug 21, 2026, 12:13:55{NNBSP}PM IST"):
    return cell(
        f"Watched{NBSP}"
        f'<a href="https://www.youtube.com/watch?v=abc">{title}</a><br>'
        f'<a href="https://www.youtube.com/channel/UCx">Chan</a><br>{stamp}<br>'
    )


def make_zip(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in members.items():
            z.writestr(name, content)
    buf.seek(0)
    return buf


def test_ingests_html_watch_history():
    zf = make_zip({f"{BASE}/history/watch-history.html": watch_cell() + watch_cell("B")})

    result = ingest_zip(zf, TZ)

    assert len(result.events) == 2
    assert all(e["type"] == "watch" for e in result.events)
    assert result.stats["total_watch"] == 2


def test_html_timestamps_are_not_double_shifted():
    """12:13 PM IST must stay 12:13 local, not become 17:43."""
    zf = make_zip({f"{BASE}/history/watch-history.html": watch_cell()})

    (event,) = ingest_zip(zf, TZ).events

    assert event["timestamp_utc"] == "2026-08-21T06:43:55Z"
    assert event["hour_local"] == 12


def test_ingests_json_watch_history():
    entries = [
        {
            "header": "YouTube",
            "title": "Watched A Video",
            "titleUrl": "https://www.youtube.com/watch?v=abc",
            "subtitles": [{"name": "Chan", "url": "https://www.youtube.com/channel/UCx"}],
            "time": "2026-08-21T06:43:55Z",
        }
    ]
    zf = make_zip({f"{BASE}/history/watch-history.json": json.dumps(entries)})

    result = ingest_zip(zf, TZ)

    assert len(result.events) == 1
    assert result.events[0]["channel"] == "Chan"


def test_json_wins_when_both_formats_are_present():
    entries = [{"title": "Watched From JSON",
                "titleUrl": "https://www.youtube.com/watch?v=j",
                "time": "2026-08-21T06:43:55Z"}]
    zf = make_zip({
        f"{BASE}/history/watch-history.json": json.dumps(entries),
        f"{BASE}/history/watch-history.html": watch_cell("From HTML"),
    })

    (event,) = ingest_zip(zf, TZ).events

    assert event["text_raw"] == "From JSON"


def test_zip_without_history_yields_no_events():
    zf = make_zip({f"{BASE}/playlists/x.csv": "a,b\n1,2\n"})

    result = ingest_zip(zf, TZ)

    assert result.events == []


def test_subscriptions_are_ingested():
    csv = "Channel Id,Channel Url,Channel Title\nUCx,https://youtube.com/channel/UCx,Chan\n"
    zf = make_zip({f"{BASE}/subscriptions/subscriptions.csv": csv})

    result = ingest_zip(zf, TZ)

    assert result.stats["total_subscribe"] == 1


def test_report_counts_cells_and_drops():
    """Kept above MIN_YIELD so this exercises reporting, not the threshold."""
    good = "".join(watch_cell(f"G{i}") for i in range(9))
    zf = make_zip({
        f"{BASE}/history/watch-history.html": good + watch_cell("B", stamp="nope")
    })

    result = ingest_zip(zf, TZ)

    assert result.report["watch"]["cells_seen"] == 10
    assert result.report["watch"]["entries_emitted"] == 9
    assert sum(result.report["watch"]["dropped"].values()) == 1


def test_low_yield_fails_loudly_rather_than_returning_partial_data():
    """A systematic format mismatch must not silently produce a plausible Wrapped."""
    good = watch_cell()
    bad = "".join(watch_cell(f"B{i}", stamp="21/08/2026 nope") for i in range(9))
    zf = make_zip({f"{BASE}/history/watch-history.html": good + bad})

    with pytest.raises(HistoryParseError) as excinfo:
        ingest_zip(zf, TZ)

    assert "BAD_FORMAT" in str(excinfo.value)


def test_yield_at_the_threshold_is_accepted():
    good = "".join(watch_cell(f"G{i}") for i in range(8))
    bad = "".join(watch_cell(f"B{i}", stamp="nope") for i in range(2))
    zf = make_zip({f"{BASE}/history/watch-history.html": good + bad})

    result = ingest_zip(zf, TZ)

    assert len(result.events) == 8
    assert MIN_YIELD == 0.8


def test_accepts_raw_bytes_as_well_as_a_file_object():
    zf = make_zip({f"{BASE}/history/watch-history.html": watch_cell()})
    raw = zf.getvalue()

    assert len(ingest_zip(raw, TZ).events) == 1


# --- year filtering ---------------------------------------------------------------

def stamped(title, year, month="Aug", day="21"):
    return watch_cell(title, stamp=f"{month} {day}, {year}, 12:13:55{NNBSP}PM IST")


def multi_year_zip():
    return make_zip({
        f"{BASE}/history/watch-history.html": (
            stamped("A", 2026) + stamped("B", 2026) + stamped("C", 2025)
        )
    })


def test_filters_to_the_requested_year():
    result = ingest_zip(multi_year_zip(), TZ, year=2025)

    assert result.year == 2025
    assert len(result.events) == 1
    assert result.events[0]["text_raw"] == "C"


def test_reports_which_years_have_data():
    result = ingest_zip(multi_year_zip(), TZ, year=2026)

    assert result.years_available == [2025, 2026]


def test_defaults_to_the_most_recent_year_when_current_year_is_absent():
    """No year requested and no 2026-equivalent data: fall back, don't return empty."""
    zf = make_zip({f"{BASE}/history/watch-history.html": stamped("Old", 2021)})

    result = ingest_zip(zf, TZ)

    assert result.year == 2021
    assert len(result.events) == 1


def test_requested_year_with_no_data_yields_no_watch_events():
    result = ingest_zip(multi_year_zip(), TZ, year=2019)

    assert result.year == 2019
    assert result.stats["total_watch"] == 0
    assert result.years_available == [2025, 2026]


def test_year_boundary_is_local_not_utc():
    """20:30 Dec 31 UTC is 02:00 Jan 1 in Kolkata, so this belongs to 2026."""
    zf = make_zip({
        f"{BASE}/history/watch-history.html": watch_cell(
            "NewYear", stamp=f"Jan 1, 2026, 2:00:00{NNBSP}AM IST"
        )
    })

    result = ingest_zip(zf, TZ, year=2026)

    assert len(result.events) == 1
    assert result.events[0]["timestamp_utc"] == "2025-12-31T20:30:00Z"


def test_subscriptions_survive_year_filtering():
    """subscriptions.csv has no date column, so it must be exempt or the card empties."""
    csv = "Channel Id,Channel Url,Channel Title\nUCx,https://youtube.com/channel/UCx,Chan\n"
    zf = make_zip({
        f"{BASE}/history/watch-history.html": stamped("A", 2026),
        f"{BASE}/subscriptions/subscriptions.csv": csv,
    })

    result = ingest_zip(zf, TZ, year=2019)

    assert result.stats["total_watch"] == 0
    assert result.stats["total_subscribe"] == 1


def test_search_history_is_filtered_to_the_same_year():
    search = cell(
        f"Searched for{NBSP}"
        '<a href="https://www.youtube.com/results?search_query=x">x</a><br>'
        f"Aug 21, 2022, 12:13:55{NNBSP}PM IST<br>"
    )
    zf = make_zip({
        f"{BASE}/history/watch-history.html": stamped("A", 2026),
        f"{BASE}/history/search-history.html": search,
    })

    result = ingest_zip(zf, TZ, year=2026)

    assert result.stats["total_watch"] == 1
    assert result.stats["total_search"] == 0
