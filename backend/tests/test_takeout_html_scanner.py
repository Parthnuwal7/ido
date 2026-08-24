"""Tests for takeout_html_scanner: Takeout HTML -> raw cell records.

Fixtures mirror the real export template byte-for-byte, including the U+00A0 after the
activity verb and the U+202F before the meridiem.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.takeout_html_scanner import scan  # noqa: E402

NBSP = "\xa0"
NNBSP = " "  # U+202F

CAPTION_PLAIN = (
    "<b>Products:</b><br>&emsp;YouTube<br><b>Why is this here?</b><br>"
    "&emsp;This activity was saved to your Google Account."
)
CAPTION_AD = (
    "<b>Products:</b><br>&emsp;YouTube<br><b>Details:</b><br>&emsp;From Google Ads<br>"
    "<b>Why is this here?</b><br>&emsp;This activity was saved to your Google Account."
)


def cell(body, product="YouTube", caption=CAPTION_PLAIN):
    """Build one outer-cell exactly as Takeout emits it."""
    return (
        '<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">'
        '<div class="mdl-grid">'
        '<div class="header-cell mdl-cell mdl-cell--12-col">'
        f'<p class="mdl-typography--title">{product}<br></p></div>'
        '<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">'
        f"{body}</div>"
        '<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1 '
        'mdl-typography--text-right"></div>'
        '<div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">'
        f"{caption}</div></div></div>"
    )


NORMAL_BODY = (
    f"Watched{NBSP}"
    '<a href="https://www.youtube.com/watch?v=gZDzL1uyJdw">Big Political Shift</a><br>'
    '<a href="https://www.youtube.com/channel/UCpg-rSVxo3EgwEmWHl2nN9A">AstroKapoor</a>'
    f"<br>Aug 21, 2026, 12:13:55{NNBSP}PM IST<br>"
)


def test_scans_a_normal_video_cell():
    (record,) = list(scan(cell(NORMAL_BODY)))

    assert record["product"] == "YouTube"
    assert record["prefix"] == "Watched"
    assert record["links"] == [
        ("https://www.youtube.com/watch?v=gZDzL1uyJdw", "Big Political Shift"),
        ("https://www.youtube.com/channel/UCpg-rSVxo3EgwEmWHl2nN9A", "AstroKapoor"),
    ]
    assert record["timestamp"] == f"Aug 21, 2026, 12:13:55{NNBSP}PM IST"
    assert record["is_ad"] is False


def test_detects_ad_from_caption_when_body_looks_normal():
    """1,420 of 1,536 ads have a normal title; the only tell is in the caption cell."""
    (record,) = list(scan(cell(NORMAL_BODY, caption=CAPTION_AD)))

    assert record["is_ad"] is True
    assert record["prefix"] == "Watched"


def test_scans_youtube_music_product():
    body = (
        f"Watched{NBSP}"
        '<a href="https://music.youtube.com/watch?v=Zsd4TyucE40">remember to rest</a>'
        '<br><a href="https://www.youtube.com/channel/UCnG5">Daniel Saint - Topic</a>'
        f"<br>Aug 20, 2026, 12:55:19{NNBSP}PM IST<br>"
    )

    (record,) = list(scan(cell(body, product="YouTube Music")))

    assert record["product"] == "YouTube Music"
    assert record["links"][0][0].startswith("https://music.youtube.com/")


def test_scans_link_less_activity_cell():
    body = f"Viewed a post that is no longer available<br>Aug 20, 2026, 5:11:31{NNBSP}PM IST<br>"

    (record,) = list(scan(cell(body)))

    assert record["links"] == []
    assert record["prefix"] == "Viewed a post that is no longer available"
    assert record["timestamp"] == f"Aug 20, 2026, 5:11:31{NNBSP}PM IST"


def test_unescapes_html_entities_in_anchor_text():
    """The JSON export carries the real character, so the connector must decode."""
    body = (
        f"Watched{NBSP}"
        '<a href="https://music.youtube.com/watch?v=X">slowed &amp; reverb</a><br>'
        '<a href="https://www.youtube.com/channel/UCn">Artist</a><br>'
        f"Aug 20, 2026, 12:55:19{NNBSP}PM IST<br>"
    )

    (record,) = list(scan(cell(body)))

    assert record["links"][0][1] == "slowed & reverb"


def test_scans_multiple_cells_in_document_order():
    second = NORMAL_BODY.replace("Big Political Shift", "Second Video")

    records = list(scan(cell(NORMAL_BODY) + cell(second)))

    assert [r["links"][0][1] for r in records] == ["Big Political Shift", "Second Video"]


def test_cell_without_a_body_is_skipped():
    broken = (
        '<div class="outer-cell mdl-cell"><div class="mdl-grid">'
        '<div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">'
        f"{CAPTION_PLAIN}</div></div></div>"
    )

    assert list(scan(broken + cell(NORMAL_BODY))) == list(scan(cell(NORMAL_BODY)))


def test_cell_without_a_timestamp_yields_none():
    body = f"Watched{NBSP}<a href=\"https://www.youtube.com/watch?v=X\">Title</a><br>"

    (record,) = list(scan(cell(body)))

    assert record["timestamp"] is None


def test_empty_document_yields_nothing():
    assert list(scan("")) == []
