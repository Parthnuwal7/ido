"""Tests for discovery: novelty and concentration across the year.

The interesting case is the two moving in opposite directions -- fewer new channels
found, but attention spread across more of the known ones.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.discovery import MIN_MONTHS, analyse  # noqa: E402


def watch(month, channel, day=1):
    when = datetime(2026, month, day, 20, 0)
    return {
        "type": "watch",
        "channel_clean": channel,
        "timestamp_local": when.isoformat(),
        "month_local": month,
    }


def test_first_month_is_all_new_channels():
    events = [watch(1, f"chan{i}") for i in range(10)]

    (first,) = analyse(events)["months"]

    assert first["novelty_rate"] == 1.0
    assert first["new_channels"] == 10


def test_revisiting_known_channels_lowers_novelty():
    events = [watch(1, f"chan{i}") for i in range(10)]
    events += [watch(2, f"chan{i}") for i in range(10)]

    months = analyse(events)["months"]

    assert months[0]["novelty_rate"] == 1.0
    assert months[1]["novelty_rate"] == 0.0


def test_months_are_reported_in_order():
    events = [watch(3, "a"), watch(1, "b"), watch(2, "c")]

    months = [m["month"] for m in analyse(events)["months"]]

    assert months == sorted(months)


def test_concentration_is_the_top_ten_share():
    """10 channels once each plus one channel 90 times: top-10 dominates."""
    events = [watch(1, f"chan{i}") for i in range(10)]
    events += [watch(1, "hot", day=2) for _ in range(90)]

    (first,) = analyse(events)["months"]

    assert first["top10_share"] > 0.9
    assert first["distinct"] == 11


def test_falling_novelty_with_falling_concentration_is_summarised():
    events = []
    for i in range(60):
        events.append(watch(1, f"new{i}"))
    for month in (2, 3, 4):
        for i in range(60):
            events.append(watch(month, f"new{i % 50}", day=2))

    result = analyse(events)

    assert result["novelty_end"] < result["novelty_start"]
    assert result["summary"] in {
        "narrowing_but_spreading", "narrowing", "widening", "steady"
    }


def test_too_few_months_reports_insufficient_data():
    events = [watch(1, "a"), watch(1, "b")]

    result = analyse(events)

    assert result["summary"] == "insufficient_data"
    assert MIN_MONTHS == 3


def test_empty_history_does_not_crash():
    result = analyse([])

    assert result["months"] == []
    assert result["summary"] == "insufficient_data"


def test_events_without_timestamps_are_ignored():
    events = [watch(1, "a"), {"type": "watch", "channel_clean": "b"}]

    (first,) = analyse(events)["months"]

    assert first["watches"] == 1
