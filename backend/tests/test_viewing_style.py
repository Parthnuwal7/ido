"""Tests for viewing_style: how the user watches, from gaps alone.

Takeout does not label Shorts (86 /shorts/ URLs against 41,168 /watch?v= in the
reference export), so rapid-fire viewing is inferred from timing. These tests pin that
the metric discriminates: tightly-spaced viewing reads high, evenly-spaced reads ~zero.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.viewing_style import analyse  # noqa: E402

START = datetime(2026, 3, 2, 20, 0)


def watch(offset_minutes, channel="chan"):
    when = START + timedelta(minutes=offset_minutes)
    return {
        "type": "watch",
        "channel_clean": channel,
        "timestamp_local": when.isoformat(),
        "hour_local": when.hour,
    }


def spaced(count, minutes_apart, channel="chan"):
    return [watch(i * minutes_apart, channel) for i in range(count)]


def test_tightly_spaced_watching_reads_as_rapid():
    result = analyse(spaced(30, 1))

    assert result["rapid_share"] > 0.9
    assert result["longest_chain"] == 30


def test_evenly_spaced_watching_is_not_rapid():
    """The control: 8 minutes apart is long-form viewing, not swiping."""
    result = analyse(spaced(30, 8))

    assert result["rapid_share"] == 0.0
    assert result["considered_watches"] == 30


def test_rapid_and_considered_partition_all_watches():
    events = spaced(10, 1) + [watch(500 + i * 9) for i in range(10)]

    result = analyse(events)

    assert result["rapid_watches"] + result["considered_watches"] == len(events)


def test_longest_chain_reports_its_duration():
    result = analyse(spaced(20, 1))

    assert result["longest_chain"] == 20
    assert result["longest_chain_minutes"] == 19.0


def test_median_gap_is_reported():
    assert analyse(spaced(11, 4))["median_gap_minutes"] == 4.0


def test_staying_on_one_channel_reads_as_bingeing():
    result = analyse(spaced(20, 5, channel="same"))

    assert result["run_share"] > 0.9
    assert result["style"] == "bingeing"


def test_hopping_between_channels_reads_as_grazing():
    events = [watch(i * 5, channel=f"chan{i}") for i in range(20)]

    result = analyse(events)

    assert result["run_share"] == 0.0
    assert result["style"] == "grazer"


def test_result_declares_that_rapid_fire_is_inferred():
    """Takeout never labels Shorts; the card must say timing is the basis."""
    assert analyse(spaced(5, 1))["inferred_from_timing"] is True


def test_empty_and_single_event_histories_do_not_crash():
    for events in ([], [watch(0)]):
        result = analyse(events)
        assert result["rapid_share"] == 0.0
        assert result["longest_chain"] in (0, 1)


def test_events_without_timestamps_are_ignored():
    result = analyse(spaced(5, 1) + [{"type": "watch", "channel_clean": "x"}])

    assert result["rapid_watches"] + result["considered_watches"] == 5
