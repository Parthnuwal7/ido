"""
How the user watches, inferred from the gaps between watches.

Takeout does not mark Shorts -- the reference export has 86 /shorts/ URLs against
41,168 /watch?v= -- so a swipe and a deliberate view are indistinguishable except by
timing. A gap under RAPID_GAP_MINUTES means the previous video cannot have been watched
through, and a long chain of those is the signature of scrolling.

This is an inference, not a label, and every result says so via `inferred_from_timing`.
"""

from datetime import datetime
from statistics import median
from typing import Dict, List, Optional

# Under this, the previous video cannot have finished. Validated to discriminate:
# 76-80% on Shorts-heavy real history vs 0.8% on long-form synthetic history.
RAPID_GAP_MINUTES = 2.0
# A same-channel run is only a run if the watches are contiguous in one sitting.
RUN_GAP_MINUTES = 30
# Above this share of watches inside same-channel runs of 3+, the viewer is staying
# with creators rather than hopping between them.
LOYAL_RUN_SHARE = 0.15
# Above this share of rapid-fire watches, the viewer is scrolling rather than watching.
SCROLLING_SHARE = 0.5

MIN_RUN_LENGTH = 3


def _timeline(watch_events: List[Dict]):
    """(datetime, channel) pairs in order, skipping events we cannot place in time."""
    out = []
    for event in watch_events:
        stamp = event.get("timestamp_local") or event.get("timestamp_utc")
        if not stamp:
            continue
        try:
            out.append(
                (datetime.fromisoformat(stamp.replace("Z", "+00:00")),
                 event.get("channel_clean"))
            )
        except (ValueError, AttributeError):
            continue
    out.sort(key=lambda pair: pair[0])
    return out


def _style(rapid_share: float, run_share: float) -> str:
    """A label that accounts for BOTH numbers on the card.

    Pace and loyalty are independent: how fast you move between videos says nothing
    about whether you stay with one creator. Deriving the label from loyalty alone
    made two opposite viewers read the same -- one who watched 99% of videos through
    and one who swiped past 78% were both called a "grazer", directly contradicting
    the headline percentage sitting beside it.

                        hops between creators   stays with a creator
      watches fully     explorer                deep_diver
      scrolls fast      scroller                binge_scroller
    """
    scrolling = rapid_share >= SCROLLING_SHARE
    loyal = run_share >= LOYAL_RUN_SHARE

    if scrolling:
        return "binge_scroller" if loyal else "scroller"
    return "deep_diver" if loyal else "explorer"


def _empty() -> Dict:
    return {
        "rapid_share": 0.0,
        "rapid_watches": 0,
        "considered_watches": 0,
        "longest_chain": 0,
        "longest_chain_minutes": 0.0,
        "median_gap_minutes": 0.0,
        "run_share": 0.0,
        "style": "explorer",
        "inferred_from_timing": True,
    }


def analyse(watch_events: List[Dict]) -> Dict:
    """Rapid-fire share, longest chain, and the viewer style both imply."""
    timeline = _timeline(watch_events)
    total = len(timeline)
    if total == 0:
        return _empty()
    if total == 1:
        result = _empty()
        result["longest_chain"] = 1
        result["considered_watches"] = 1
        return result

    gaps = [
        (timeline[i + 1][0] - timeline[i][0]).total_seconds() / 60
        for i in range(total - 1)
    ]

    # Chains: a run of consecutive sub-threshold gaps, plus the watch that starts it.
    chains = []
    chain_start: Optional[int] = None
    for index, gap in enumerate(gaps):
        if gap < RAPID_GAP_MINUTES:
            if chain_start is None:
                chain_start = index
        elif chain_start is not None:
            chains.append((chain_start, index))
            chain_start = None
    if chain_start is not None:
        chains.append((chain_start, len(gaps)))

    rapid_watches = sum(end - start + 1 for start, end in chains)
    longest = max(chains, key=lambda c: c[1] - c[0], default=None)
    longest_length = (longest[1] - longest[0] + 1) if longest else 0
    longest_minutes = (
        (timeline[longest[1]][0] - timeline[longest[0]][0]).total_seconds() / 60
        if longest else 0.0
    )

    # Same-channel runs: consecutive watches of one channel inside a single sitting.
    runs = []
    current = 1
    for index in range(1, total):
        same_channel = timeline[index][1] == timeline[index - 1][1]
        close_enough = gaps[index - 1] <= RUN_GAP_MINUTES
        if same_channel and close_enough:
            current += 1
        else:
            runs.append(current)
            current = 1
    runs.append(current)
    in_runs = sum(length for length in runs if length >= MIN_RUN_LENGTH)
    run_share = in_runs / total

    return {
        "rapid_share": round(rapid_watches / total, 4),
        "rapid_watches": rapid_watches,
        "considered_watches": total - rapid_watches,
        "longest_chain": longest_length,
        "longest_chain_minutes": round(longest_minutes, 1),
        "median_gap_minutes": round(median(gaps), 1),
        "run_share": round(run_share, 4),
        "style": _style(rapid_watches / total, run_share),
        "inferred_from_timing": True,
    }
