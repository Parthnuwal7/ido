"""Tests for pattern_mining: association rules over watch history.

The headline regression here is the channel-eligibility gate. It used to be
max(10, len(watch_events)//100), which scales with total watches -- so a user with
20,626 watches needed 206 on a single channel to be considered, and got zero patterns
while a user with 1,000 watches got plenty. Heavier use produced fewer insights.
"""
import collections
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.pattern_mining import (  # noqa: E402
    MIN_SUPPORT,
    channel_day_rules,
    channel_slot_rules,
    cooccurrence_rules,
    find_patterns,
    opener_rules,
    seasonal_rules,
    top_channels,
)

BASE = datetime(2026, 3, 1, 9, 0)  # a Sunday


def watch(channel, when):
    return {
        "type": "watch",
        "channel_clean": channel,
        "timestamp_local": when.isoformat(),
        "hour_local": when.hour,
        "day_of_week": when.weekday(),
        "month_local": when.month,
        "text_clean": f"{channel} video",
    }


def spread(channel, count, start=BASE, step_days=7, hour=None):
    """`count` watches of one channel, one per step_days, optionally pinned to an hour."""
    out = []
    for i in range(count):
        when = start + timedelta(days=i * step_days)
        if hour is not None:
            when = when.replace(hour=hour)
        out.append(watch(channel, when))
    return out


# --- channel eligibility ----------------------------------------------------------

def test_gate_is_an_absolute_floor_not_a_proportion():
    """The regression: a heavy watcher must not be gated out of their own patterns."""
    events = spread("habit", 40) + [
        watch(f"noise{i}", BASE + timedelta(hours=i)) for i in range(20000)
    ]

    assert "habit" in top_channels(events)


def test_channels_below_the_floor_are_excluded():
    events = spread("rare", MIN_SUPPORT - 1) + spread("common", MIN_SUPPORT + 5)

    selected = top_channels(events)

    assert "common" in selected
    assert "rare" not in selected


def test_no_channels_yields_empty_selection():
    assert top_channels([]) == set()


# --- individual rule types --------------------------------------------------------

def test_finds_a_day_of_week_habit():
    """Every watch on a Sunday: confidence 1.0, well above the 1/7 baseline."""
    events = spread("sunday show", 20) + spread("filler", 20, step_days=1)

    rules = channel_day_rules(events, {"sunday show", "filler"})

    sunday = [r for r in rules if r["channel"] == "sunday show"]
    assert sunday, "expected a Sunday pattern"
    assert sunday[0]["day"] == "Sunday"
    assert sunday[0]["confidence"] == 1.0


def test_finds_a_time_of_day_habit():
    events = spread("morning show", 20, step_days=1, hour=7) + spread(
        "evening show", 20, step_days=1, hour=20
    )

    rules = channel_slot_rules(events, {"morning show", "evening show"})

    morning = [r for r in rules if r["channel"] == "morning show"]
    assert morning and morning[0]["slot"] == "morning"


def test_finds_channels_watched_together_in_a_session():
    """Two channels always in the same sitting -- the association the README promises."""
    events = []
    for i in range(20):
        start = BASE + timedelta(days=i)
        events.append(watch("artist a", start))
        events.append(watch("artist b", start + timedelta(minutes=5)))
    # Enough unrelated sessions that the pair's base rate is low -- with only a handful
    # of sessions, two channels in half of them is barely above chance by construction.
    for i in range(180):
        events.append(watch(f"other {i}", BASE + timedelta(days=100 + i)))

    rules = cooccurrence_rules(events)

    pairs = {frozenset((r["channel_a"], r["channel_b"])) for r in rules}
    assert frozenset(("artist a", "artist b")) in pairs


def test_cooccurrence_ignores_channels_that_never_share_a_session():
    events = []
    for i in range(20):
        events.append(watch("solo a", BASE + timedelta(days=i)))
        events.append(watch("solo b", BASE + timedelta(days=i, hours=6)))

    rules = cooccurrence_rules(events)

    assert not [
        r for r in rules
        if {r["channel_a"], r["channel_b"]} == {"solo a", "solo b"}
    ]


def test_finds_a_session_opening_channel():
    events = []
    for i in range(20):
        start = BASE + timedelta(days=i)
        events.append(watch("opener", start))
        events.append(watch("follower", start + timedelta(minutes=10)))

    rules = opener_rules(events)

    assert rules and rules[0]["channel"] == "opener"


# --- orchestration ----------------------------------------------------------------

def test_find_patterns_respects_the_limit():
    events = []
    for name in "abcdefgh":
        events += spread(f"channel {name}", 20, hour=7, step_days=1)

    assert len(find_patterns(events, limit=3)) <= 3


def test_find_patterns_sorts_strongest_first():
    events = spread("strong", 30, step_days=7) + spread("weak", 30, step_days=1)

    patterns = find_patterns(events)

    if len(patterns) > 1:
        scores = [p["lift"] * p["confidence"] for p in patterns]
        assert scores == sorted(scores, reverse=True)


def test_find_patterns_on_empty_input():
    assert find_patterns([]) == []


def test_every_pattern_carries_its_evidence():
    events = spread("sunday show", 25)

    for pattern in find_patterns(events):
        assert pattern["count"] >= 1
        assert 0 < pattern["confidence"] <= 1
        assert pattern["lift"] > 0
        assert pattern["insight"]


# --- rule quality -----------------------------------------------------------------

def test_a_channel_only_ever_watched_in_one_month_is_not_seasonal():
    """A channel discovered in April and dropped is not a season -- it never had the
    chance to appear elsewhere, so concentration carries no information."""
    discovered = [watch("short lived", datetime(2026, 4, d, 20)) for d in range(1, 26)]
    spread_out = [
        watch("always on", datetime(2026, m, d, 20))
        for m in range(1, 9) for d in (1, 10, 20)
    ]

    rules = seasonal_rules(discovered + spread_out, {"short lived", "always on"})

    assert not [r for r in rules if r["channel"] == "short lived"]


def test_a_channel_watched_year_round_but_peaking_is_seasonal():
    """The real signal: present across the year, concentrated in its season."""
    events = []
    for month in range(1, 9):
        for day in range(1, 4):
            events.append(watch("sport", datetime(2026, month, day, 20)))
    for day in range(1, 31):
        events.append(watch("sport", datetime(2026, 4, day, 20)))
    # Background viewing spread evenly, so April is unremarkable overall and the
    # channel has something to deviate from.
    for month in range(1, 9):
        for day in range(1, 26):
            events.append(watch("background", datetime(2026, month, day, 20)))

    rules = seasonal_rules(events, {"sport", "background"})

    assert rules and rules[0]["month"] == "April"


def test_no_single_rule_type_floods_the_card():
    """Five insights of the same shape read as a bug, not a discovery."""
    events = []
    for i in range(6):
        name = f"seasonal {i}"
        for month in range(1, 9):
            events += [watch(name, datetime(2026, month, d, 20)) for d in (1, 2)]
        events += [watch(name, datetime(2026, 7, d, 20)) for d in range(1, 26)]

    patterns = find_patterns(events, limit=5)

    kinds = collections.Counter(p["type"] for p in patterns)
    assert max(kinds.values()) <= 2, f"one type dominated: {kinds}"
