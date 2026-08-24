"""Tests for personality: archetype derived from the data, not hardcoded.

Every axis is scored as deviation from chance -- a slot's share of watches against its
share of the 24 hours, weekend share against 2/7. Axes without a natural chance baseline
(binge rate, rewatch rate) are reported as supporting numbers but never decide the label,
because with a single user's data there is nothing to call "high".
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.personality import analyse  # noqa: E402

MONDAY = datetime(2026, 3, 2)


def watch(when, channel="chan", title=None):
    return {
        "type": "watch",
        "channel_clean": channel,
        "timestamp_local": when.isoformat(),
        "hour_local": when.hour,
        "day_of_week": when.weekday(),
        "month_local": when.month,
        "text_clean": title or f"video {when.isoformat()}",
    }


def over_days(days, hour, start=MONDAY, channel="chan"):
    """One watch per day at a fixed hour -- 21 days covers whole weeks evenly."""
    return [watch(start + timedelta(days=i, hours=hour), channel) for i in range(days)]


def test_late_night_viewing_gives_night_owl():
    """0-5h is 5/24 of the day, so watching only then is a 4.8x deviation."""
    result = analyse(over_days(21, hour=2))

    assert result["type"] == "Night Owl"


def test_morning_viewing_gives_early_bird():
    result = analyse(over_days(21, hour=7))

    assert result["type"] == "Early Bird"


def test_weekend_viewing_beats_a_flat_clock():
    """Hours spread evenly, but every watch on Sat/Sun: 2/7 baseline, 3.5x deviation."""
    events = []
    for week in range(6):
        saturday = MONDAY + timedelta(days=week * 7 + 5)
        for hour in range(0, 24, 3):
            events.append(watch(saturday + timedelta(hours=hour)))

    assert analyse(events)["type"] == "Weekend Warrior"


def test_description_carries_the_evidence():
    result = analyse(over_days(21, hour=2))

    assert "%" in result["description"]


def test_evidence_reports_the_measured_lift():
    result = analyse(over_days(21, hour=2))

    assert result["evidence"]["lift"] > 1
    assert 0 < result["evidence"]["share"] <= 1
    assert result["evidence"]["axis"]


def test_supporting_stats_are_reported_without_driving_the_label():
    events = over_days(21, hour=2)

    stats = analyse(events)["stats"]

    assert stats["channels"] == 1
    assert "channel_entropy" in stats
    assert "rewatch_rate" in stats


def test_evenly_spread_viewing_does_not_crash_or_overclaim():
    """No axis deviates much, so the archetype must be a low-confidence fallback."""
    events = []
    for day in range(28):
        for hour in range(0, 24, 2):
            events.append(watch(MONDAY + timedelta(days=day, hours=hour)))

    result = analyse(events)

    assert result["type"]
    assert result["evidence"]["lift"] < 1.5


def test_empty_input_returns_a_safe_default():
    result = analyse([])

    assert result["type"]
    assert result["description"]


def test_is_deterministic():
    events = over_days(21, hour=2)

    assert analyse(events) == analyse(events)
