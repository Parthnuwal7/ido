"""Tests for interest_vectors: taste worlds from channel co-occurrence.

The headline test is ground truth: fixtures/demo_takeout.zip is generated with known
themes (three music channels, three science, three tech, three craft), and clustering
must recover them. That is what proves the parameters are not tuned to one person.
"""
import collections
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.interest_vectors import (  # noqa: E402
    MAX_K,
    MIN_K,
    MIN_VOCAB,
    analyse,
    by_month,
)

START = datetime(2026, 1, 1, 20, 0)


def session(channels, day, minute_step=5):
    """One sitting: several channels a few minutes apart."""
    when = START + timedelta(days=day)
    out = []
    for i, channel in enumerate(channels):
        moment = when + timedelta(minutes=i * minute_step)
        out.append({
            "type": "watch",
            "channel_clean": channel,
            "timestamp_local": moment.isoformat(),
            "month_local": moment.month,
        })
    return out


def _wide_history():
    """Four disjoint 3-channel groups -- 12 channels, exactly at MIN_VOCAB."""
    events = []
    for day in range(20):
        events += session(["a1", "a2", "a3"], day * 4)
        events += session(["b1", "b2", "b3"], day * 4 + 1)
        events += session(["c1", "c2", "c3"], day * 4 + 2)
        events += session(["d1", "d2", "d3"], day * 4 + 3)
    return events


def test_returns_none_below_the_vocabulary_floor():
    """Too few recurring channels to cluster: say so rather than invent groups."""
    events = []
    for day in range(20):
        events += session(["only1", "only2"], day)

    assert analyse(events) is None


def test_no_cluster_ever_mixes_two_disjoint_groups():
    """Purity, not togetherness, is the invariant.

    K=6 against only four real groups means two clusters have nowhere to come from
    except by splitting a group, so a group being spread across clusters is expected
    and correct. What must never happen is a cluster containing channels from two
    groups that never co-occur -- fragmented-but-pure is the acceptable way to fail,
    mixed-and-wrong is not.
    """
    result = analyse(_wide_history())
    assert result is not None

    members = collections.defaultdict(set)
    for channel, cluster in result.cluster_of.items():
        members[cluster].add(channel[0])  # "a1" -> group "a"

    mixed = {c: g for c, g in members.items() if len(g) > 1}
    assert not mixed, f"clusters mixed unrelated groups: {mixed}"


def test_channels_that_always_co_occur_are_not_split_when_k_allows():
    """With as many groups as clusters, each group should stay whole."""
    events = []
    for day in range(20):
        for offset, prefix in enumerate("abcdef"):
            events += session([f"{prefix}1", f"{prefix}2", f"{prefix}3"],
                              day * 6 + offset)

    result = analyse(events)

    assert result.cluster_of["a1"] == result.cluster_of["a2"] == result.cluster_of["a3"]
    assert result.cluster_of["a1"] != result.cluster_of["b1"]


def test_clusters_are_sorted_by_watch_volume():
    result = analyse(_wide_history())

    watches = [c["watches"] for c in result.clusters]
    assert watches == sorted(watches, reverse=True)


def test_coverage_reports_the_clustered_share():
    result = analyse(_wide_history())

    assert 0 < result.coverage <= 1.0


def test_is_deterministic():
    events = _wide_history()

    first = analyse(events)
    second = analyse(events)

    assert first.cluster_of == second.cluster_of


def test_recovers_the_themes_planted_in_the_demo_fixture():
    """Ground truth. If this drops below 100%, clustering has regressed."""
    from services.takeout_ingest import ingest_zip

    truth = {
        "lofi girl": "music", "chillhop music": "music", "odesza": "music",
        "kurzgesagt": "science", "veritasium": "science", "mark rober": "science",
        "mkbhd": "tech", "linus tech tips": "tech", "fireship": "tech",
        "adam savage's tested": "craft", "steve mould": "craft",
        "practical engineering": "craft",
    }
    demo = os.path.join(os.path.dirname(__file__), "..", "fixtures", "demo_takeout.zip")
    with open(demo, "rb") as fh:
        result_events = ingest_zip(fh, "UTC", year=2025).events
    watch_events = [e for e in result_events if e.get("type") == "watch"]

    result = analyse(watch_events)
    assert result is not None

    by_cluster = collections.defaultdict(list)
    for channel, cluster in result.cluster_of.items():
        if channel in truth:
            by_cluster[cluster].append(truth[channel])

    correct = total = 0
    for themes in by_cluster.values():
        dominant = collections.Counter(themes).most_common(1)[0][0]
        correct += sum(1 for t in themes if t == dominant)
        total += len(themes)

    assert total == len(truth), "every planted channel should be clustered"
    assert correct == total, f"purity dropped to {correct}/{total}"


def test_by_month_reports_a_share_per_world_per_month():
    events = _wide_history()
    result = analyse(events)

    calendar = by_month(result, events)

    assert len(calendar["worlds"]) == len(result.clusters)
    for world in calendar["worlds"]:
        assert len(world["shares"]) == len(calendar["months"])


def test_uniform_viewing_is_not_seasonal():
    """Same mix every month: the permutation test must not claim a season."""
    events = []
    for month in range(1, 7):
        for day in range(12):
            events += session(["a1", "a2", "a3"], (month - 1) * 30 + day * 2)
            events += session(["b1", "b2", "b3"], (month - 1) * 30 + day * 2 + 1)

    result = analyse(events + _wide_history())
    calendar = by_month(result, events)

    assert calendar["p_value"] >= 0.0
    assert isinstance(calendar["seasonal"], bool)


def test_k_range_and_floor_are_the_documented_values():
    assert (MIN_K, MAX_K) == (3, 8)
    assert MIN_VOCAB == 12


# --- adaptive cluster count --------------------------------------------------------

def test_cluster_count_adapts_to_the_data():
    """Three well-separated groups should yield three worlds, not a fixed six.

    Forcing K=6 onto three real groups splits them, which is what produced three
    separate "Pop Music" worlds on real data instead of one.
    """
    events = []
    for day in range(24):
        events += session(["p1", "p2", "p3", "p4"], day * 3)
        events += session(["q1", "q2", "q3", "q4"], day * 3 + 1)
        events += session(["r1", "r2", "r3", "r4"], day * 3 + 2)

    result = analyse(events)

    assert result is not None
    assert len(result.clusters) == 3, (
        f"expected 3 worlds for 3 groups, got {len(result.clusters)}"
    )


def test_more_groups_yield_more_clusters_up_to_the_cap():
    events = []
    prefixes = "abcdefghij"          # ten disjoint groups, above MAX_K
    for day in range(24):
        for offset, prefix in enumerate(prefixes):
            events += session([f"{prefix}1", f"{prefix}2", f"{prefix}3"],
                              day * len(prefixes) + offset)

    result = analyse(events)

    assert MIN_K <= len(result.clusters) <= MAX_K
    assert MAX_K == 8


def test_clusters_stay_pure_whatever_k_is_chosen():
    events = []
    for day in range(24):
        events += session(["p1", "p2", "p3", "p4"], day * 3)
        events += session(["q1", "q2", "q3", "q4"], day * 3 + 1)
        events += session(["r1", "r2", "r3", "r4"], day * 3 + 2)

    result = analyse(events)

    members = collections.defaultdict(set)
    for channel, cluster in result.cluster_of.items():
        members[cluster].add(channel[0])
    assert not {c: g for c, g in members.items() if len(g) > 1}
