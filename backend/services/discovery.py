"""
Novelty and concentration across the year.

Two independent curves that are most interesting when they disagree:

  novelty      share of a month's watches on a channel never seen before
  top-10 share how much of a month went to that month's ten biggest channels

Falling novelty with falling concentration means the viewer stopped finding new
channels but spread attention wider across the ones they had.
"""

from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional

# Fewer than this and a trend is not a claim the data supports.
MIN_MONTHS = 3


def _month_of(event: Dict) -> Optional[str]:
    stamp = event.get("timestamp_local") or event.get("timestamp_utc")
    if not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).strftime("%Y-%m")
    except (ValueError, AttributeError):
        return None


def analyse(watch_events: List[Dict]) -> Dict:
    """Per-month novelty and concentration, plus the overall shape."""
    by_month: Dict[str, List[Dict]] = {}
    for event in watch_events:
        month = _month_of(event)
        if month and event.get("channel_clean"):
            by_month.setdefault(month, []).append(event)

    seen = set()
    months = []
    for month in sorted(by_month):
        events = by_month[month]
        counts = Counter(e["channel_clean"] for e in events)
        total = len(events)

        new_channels = 0
        for event in events:
            channel = event["channel_clean"]
            if channel not in seen:
                seen.add(channel)
                new_channels += 1

        top_ten = sum(n for _, n in counts.most_common(10))
        months.append({
            "month": month,
            "watches": total,
            "new_channels": new_channels,
            "novelty_rate": round(new_channels / total, 4),
            "top10_share": round(top_ten / total, 4),
            "distinct": len(counts),
        })

    if len(months) < MIN_MONTHS:
        return {
            "months": months,
            "novelty_start": None, "novelty_end": None,
            "concentration_start": None, "concentration_end": None,
            "summary": "insufficient_data",
        }

    novelty_start = months[0]["novelty_rate"]
    novelty_end = months[-1]["novelty_rate"]
    concentration_start = months[0]["top10_share"]
    concentration_end = months[-1]["top10_share"]

    narrowing = novelty_end < novelty_start
    spreading = concentration_end < concentration_start
    if narrowing and spreading:
        summary = "narrowing_but_spreading"
    elif narrowing:
        summary = "narrowing"
    elif not narrowing and not spreading:
        summary = "widening"
    else:
        summary = "steady"

    return {
        "months": months,
        "novelty_start": novelty_start,
        "novelty_end": novelty_end,
        "concentration_start": concentration_start,
        "concentration_end": concentration_end,
        "summary": summary,
    }
