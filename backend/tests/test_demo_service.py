"""Tests for demo_service: the seeded Wrapped served at /api/wrapped/demo.

These double as a live check on the pipeline. The demo runs the same preprocessing and
card generation as a real upload, so if a change makes patterns stop firing or the
personality collapse to a default, these fail rather than the demo quietly going bland.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.demo_service import DEMO_TAKEOUT, DEMO_YEAR, load_demo_cards  # noqa: E402


def test_produces_a_full_set_of_cards():
    cards = load_demo_cards()

    assert "error" not in cards
    assert len(cards) >= 19


def test_covers_the_demo_year():
    assert load_demo_cards()["intro"]["year"] == DEMO_YEAR


def test_headline_numbers_are_substantial():
    overview = load_demo_cards()["stats_overview"]

    assert overview["videos_watched"] > 2000
    assert overview["channels_explored"] > 100
    assert overview["active_days"] > 250


def test_personality_is_derived_not_hardcoded():
    """The seed plants a night-owl clock; the pipeline must actually detect it."""
    personality = load_demo_cards()["personality"]

    assert personality["type"] == "Night Owl"
    assert personality["evidence"]["lift"] > 1.5


def test_patterns_are_discovered():
    """A demo showing zero patterns is what this whole exercise was meant to avoid."""
    patterns = load_demo_cards()["patterns"]

    assert patterns["total_patterns"] >= 3
    assert all(p["insight"] for p in patterns["top_patterns"])


def test_patterns_span_more_than_one_rule_type():
    kinds = {p["type"] for p in load_demo_cards()["patterns"]["top_patterns"]}

    assert len(kinds) >= 2


def test_seasonal_and_social_cards_have_content():
    cards = load_demo_cards()

    assert cards["searches"]["total"] > 0
    assert cards["subscriptions"]["ghost"] > 0
    assert cards["binge_sessions"]["count"] > 0
    assert cards["longest_streak"]["days"] > 10


def test_metadata_marks_the_result_as_demo():
    metadata = load_demo_cards()["metadata"]

    assert metadata["demo"] is True
    assert metadata["year"] == DEMO_YEAR


def test_the_seed_is_a_real_takeout_archive():
    """The demo must seed a file the system processes, not pre-parsed entries."""
    import zipfile

    assert os.path.exists(DEMO_TAKEOUT)
    with zipfile.ZipFile(DEMO_TAKEOUT) as archive:
        names = archive.namelist()

    assert any(n.endswith("history/watch-history.html") for n in names)
    assert any(n.endswith("subscriptions/subscriptions.csv") for n in names)


def test_the_html_connector_actually_ran():
    """Proves the demo went through the scanner and mapper rather than around them.

    A parse report only exists when history was read from HTML; if the demo ever
    silently fell back to pre-parsed JSON, this disappears.
    """
    report = load_demo_cards()["metadata"]["parse_report"]

    assert report["watch"]["cells_seen"] == 2500
    assert report["watch"]["entries_emitted"] == 2500
    assert report["watch"]["dropped"] == {}


def test_result_is_cached_between_calls():
    """The fixtures never change at runtime, so the pipeline should run once."""
    assert load_demo_cards() is load_demo_cards()


# --- serving the archive for the upload flow ---------------------------------------

def test_demo_archive_bytes_are_readable():
    """The demo is served as a real ZIP so the browser can feed it through the same
    upload path as a user's own export, rather than a separate endpoint that skips
    the locator, the connector and year filtering."""
    from services.demo_service import demo_archive_bytes

    data = demo_archive_bytes()

    assert data[:2] == b"PK", "should be a ZIP archive"
    assert len(data) > 10_000


def test_demo_archive_round_trips_through_the_normal_ingest():
    import io
    import zipfile

    from services.demo_service import demo_archive_bytes
    from services.takeout_ingest import ingest_zip

    data = demo_archive_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert any(n.endswith("watch-history.html") for n in archive.namelist())

    result = ingest_zip(io.BytesIO(data), "UTC", year=DEMO_YEAR)
    assert result.stats["total_watch"] > 2000
