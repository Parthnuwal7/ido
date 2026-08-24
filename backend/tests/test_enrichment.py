"""Tests for enrichment: the optional network step between clustering and cards.

Enrichment must never be able to fail a Wrapped, and must never call out without both
a key and consent.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.interest_vectors import analyse  # noqa: E402
from services.takeout_ingest import build_enrichment  # noqa: E402

START = datetime(2026, 1, 1, 20, 0)


def watch(minutes, channel):
    when = START + timedelta(minutes=minutes)
    return {
        "type": "watch",
        "channel_clean": channel,
        "channel_url": f"https://www.youtube.com/channel/UC{channel:_<22.22}",
        "timestamp_local": when.isoformat(),
        "month_local": when.month,
    }


def history():
    events = []
    for day in range(20):
        base = day * 24 * 60 * 4
        groups = [("a1", "a2", "a3"), ("b1", "b2", "b3"),
                  ("c1", "c2", "c3"), ("d1", "d2", "d3")]
        for offset, group in enumerate(groups):
            for i, channel in enumerate(group):
                events.append(watch(base + offset * 24 * 60 + i * 5, channel))
    return events


def test_no_keys_configured_yields_empty_enrichment(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    events = history()

    result = build_enrichment(events, analyse(events), consented=True)

    assert result == {"names": {}, "facts": None}


def test_clustering_absent_yields_empty_enrichment(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")

    result = build_enrichment([], None, consented=True)

    assert result == {"names": {}, "facts": None}


def test_a_failing_network_call_does_not_raise(monkeypatch):
    """The whole point: enrichment degrades, it never fails the Wrapped."""
    import services.takeout_ingest as ingest

    monkeypatch.setenv("YOUTUBE_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")

    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ingest.channel_topics, "fetch", explode)
    events = history()

    result = build_enrichment(events, analyse(events), consented=True)

    assert result == {"names": {}, "facts": None}


def test_without_consent_no_names_are_requested(monkeypatch):
    import services.takeout_ingest as ingest

    monkeypatch.setenv("YOUTUBE_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(ingest.channel_topics, "fetch", lambda *a, **k: {})

    called = []
    monkeypatch.setattr(
        ingest.cluster_naming, "name_clusters",
        lambda *a, **k: called.append(True) or {},
    )
    events = history()

    build_enrichment(events, analyse(events), consented=False)

    assert called == [], "naming must not run without consent"


def test_facts_are_keyed_by_channel_name_not_channel_id(monkeypatch):
    """Cards look facts up by channel_clean, so the mapping must be translated back."""
    import services.takeout_ingest as ingest

    monkeypatch.setenv("YOUTUBE_API_KEY", "k")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    def fake_fetch(ids, key, session=None):
        return {i: {"title": i, "topics": ["Cricket"], "subscribers": 10} for i in ids}

    monkeypatch.setattr(ingest.channel_topics, "fetch", fake_fetch)
    events = history()

    result = build_enrichment(events, analyse(events), consented=False)

    assert "a1" in result["facts"]
    assert result["facts"]["a1"]["subscribers"] == 10
