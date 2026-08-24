"""Tests for the five new cards.

Gating is the point: taste_worlds and taste_calendar must be absent rather than empty
when the history cannot support them, and niche_meter must be absent without API facts.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.interest_vectors import analyse as cluster  # noqa: E402
from services.wrapped_service import (  # noqa: E402
    generate_discovery_arc_card,
    generate_niche_meter_card,
    generate_taste_calendar_card,
    generate_taste_worlds_card,
    generate_viewing_mode_card,
)

START = datetime(2026, 1, 1, 20, 0)


def watch(minutes, channel):
    when = START + timedelta(minutes=minutes)
    return {
        "type": "watch",
        "channel_clean": channel,
        "timestamp_local": when.isoformat(),
        "month_local": when.month,
    }


def clustered_history():
    """Four disjoint groups across several months -- enough to cluster."""
    events = []
    for day in range(20):
        base = day * 24 * 60 * 4
        groups = [("a1", "a2", "a3"), ("b1", "b2", "b3"),
                  ("c1", "c2", "c3"), ("d1", "d2", "d3")]
        for offset, group in enumerate(groups):
            for i, channel in enumerate(group):
                events.append(watch(base + offset * 24 * 60 + i * 5, channel))
    return events


def test_viewing_mode_card_reports_the_share_and_the_caveat():
    card = generate_viewing_mode_card([watch(i, "x") for i in range(30)])

    assert card["rapid_share"] > 0.9
    assert card["inferred_from_timing"] is True


def test_discovery_arc_card_carries_months():
    card = generate_discovery_arc_card(clustered_history())

    assert isinstance(card["months"], list)
    assert "summary" in card


def test_taste_worlds_card_uses_channel_labels_without_names():
    interest = cluster(clustered_history())

    card = generate_taste_worlds_card(interest, {})

    assert card is not None
    assert card["worlds"][0]["label"]
    assert card["worlds"][0].get("name") is None


def test_taste_worlds_card_prefers_a_real_name_when_available():
    interest = cluster(clustered_history())
    top = interest.clusters[0]["index"]

    card = generate_taste_worlds_card(interest, {top: "Cricket"})

    assert card["worlds"][0]["name"] == "Cricket"
    assert card["worlds"][0]["label"], "channel label must remain, so the name is checkable"


def test_taste_worlds_card_reports_coverage():
    """The honesty rule: clusters never describe all viewing."""
    interest = cluster(clustered_history())

    card = generate_taste_worlds_card(interest, {})

    assert 0 < card["coverage"] <= 1.0


def test_taste_worlds_card_is_none_below_the_gate():
    assert generate_taste_worlds_card(None, {}) is None


def test_taste_calendar_card_is_none_below_the_gate():
    assert generate_taste_calendar_card(None, [], {}) is None


def test_taste_calendar_card_has_a_share_per_month_per_world():
    events = clustered_history()
    interest = cluster(events)

    card = generate_taste_calendar_card(interest, events, {})

    assert card is not None
    for world in card["worlds"]:
        assert len(world["shares"]) == len(card["months"])


def test_niche_meter_is_none_without_api_facts():
    interest = cluster(clustered_history())

    assert generate_niche_meter_card(interest, None) is None


def test_niche_meter_summarises_subscriber_counts():
    interest = cluster(clustered_history())
    facts = {
        channel: {"title": channel, "topics": [], "subscribers": 1000 * (i + 1)}
        for i, channel in enumerate(interest.cluster_of)
    }

    card = generate_niche_meter_card(interest, facts)

    assert card["median_subscribers"] > 0
    assert card["channels_measured"] == len(facts)
    assert card["obscure_find"]["subscribers"] <= card["biggest"]["subscribers"]


def test_niche_meter_ignores_channels_with_no_subscriber_count():
    interest = cluster(clustered_history())
    facts = {c: {"title": c, "topics": [], "subscribers": None}
             for c in interest.cluster_of}

    assert generate_niche_meter_card(interest, facts) is None
