"""
Viewing personality, derived from the data rather than hardcoded.

Every axis is scored the same way: the observed share against the share you would
expect by chance. Watching between midnight and 5am is only remarkable because those
five hours are 5/24 of a day -- a 30% share there is a 1.44x deviation, while the same
30% share across the seven morning hours would be below chance.

    lift = observed share / chance share

Only axes with a genuine chance baseline decide the archetype: the clock (each slot's
share of 24 hours), the week (2/7 for weekends, 5/7 for weekdays) and the calendar
(one over the months the history actually spans, not one twelfth -- a Wrapped generated
in August covers eight months). Binge rate, rewatch rate and channel spread have no such
baseline --
with one user's history there is nothing to call "high" -- so they are reported as
supporting numbers and never chosen as the label. That is the difference between a
measurement and a guess, and this module only labels on measurements.
"""

import math
from collections import Counter
from typing import Dict, List, Optional

# Slot -> half-open hour range. Widths differ, which is exactly why lift is needed.
SLOTS = {
    "late night": (0, 5),
    "morning": (5, 12),
    "afternoon": (12, 17),
    "evening": (17, 21),
    "night": (21, 24),
}

SLOT_ARCHETYPE = {
    "late night": ("Night Owl", "after midnight"),
    "morning": ("Early Bird", "before noon"),
    "afternoon": ("Afternoon Regular", "in the afternoon"),
    "evening": ("Prime Timer", "in the evening"),
    "night": ("Evening Unwinder", "late in the evening"),
}

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Under this, no axis stands out enough to claim a real habit.
NOTABLE_LIFT = 1.5

# Fewer months than this and "seasonal" is not a claim the data can support.
MIN_CALENDAR_SPAN = 3

BALANCED = {
    "type": "Free Spirit",
    "description": "Your viewing does not follow any single rhythm",
}

EMPTY = {
    "type": "Newcomer",
    "description": "Not enough watch history to read a pattern yet",
    "evidence": {"axis": None, "share": 0.0, "lift": 0.0},
    "stats": {},
}


def _clock_axis(events: List[Dict]) -> Optional[Dict]:
    hours = Counter(
        e["hour_local"] for e in events if e.get("hour_local") is not None
    )
    total = sum(hours.values())
    if not total:
        return None

    best = None
    for slot, (start, end) in SLOTS.items():
        observed = sum(hours[h] for h in range(start, end)) / total
        chance = (end - start) / 24
        lift = observed / chance
        if best is None or lift > best["lift"]:
            name, phrase = SLOT_ARCHETYPE[slot]
            best = {
                "axis": f"clock:{slot}",
                "share": observed,
                "lift": lift,
                "type": name,
                "description": (
                    f"{int(observed * 100)}% of your watching happens {phrase}"
                ),
            }
    return best


def _week_axis(events: List[Dict]) -> Optional[Dict]:
    days = Counter(
        e["day_of_week"] for e in events if e.get("day_of_week") is not None
    )
    total = sum(days.values())
    if not total:
        return None

    weekend = sum(days[d] for d in (5, 6)) / total
    weekday = 1 - weekend

    if weekend / (2 / 7) >= weekday / (5 / 7):
        return {
            "axis": "week:weekend",
            "share": weekend,
            "lift": weekend / (2 / 7),
            "type": "Weekend Warrior",
            "description": (
                f"{int(weekend * 100)}% of your watching lands on Saturday and Sunday"
            ),
        }

    return {
        "axis": "week:weekday",
        "share": weekday,
        "lift": weekday / (5 / 7),
        "type": "Weekday Ritualist",
        "description": (
            f"{int(weekday * 100)}% of your watching happens Monday to Friday"
        ),
    }


def _calendar_axis(events: List[Dict]) -> Optional[Dict]:
    months = Counter(
        e["month_local"] for e in events if e.get("month_local") is not None
    )
    total = sum(months.values())
    if not total or len(months) < 2:
        return None

    # Chance is uniform across the months the history actually spans, not across 12.
    # A Wrapped generated in August covers eight months; using 1/12 would inflate every
    # month's lift by 50% and label every partial year "Seasonal Viewer".
    span = max(months) - min(months) + 1
    if span < MIN_CALENDAR_SPAN:
        return None

    month, count = months.most_common(1)[0]
    observed = count / total
    return {
        "axis": f"calendar:{month}",
        "share": observed,
        "lift": observed / (1 / span),
        "type": "Seasonal Viewer",
        "description": (
            f"{int(observed * 100)}% of your year happened in "
            f"{MONTH_NAMES[month - 1] if 1 <= month <= 12 else 'one month'}"
        ),
    }


def _supporting_stats(events: List[Dict]) -> Dict:
    """Numbers worth showing that cannot honestly be turned into a label."""
    channels = Counter(
        e.get("channel_clean") for e in events if e.get("channel_clean")
    )
    titles = Counter(e.get("text_clean") for e in events if e.get("text_clean"))
    total = sum(channels.values())

    entropy = 0.0
    if total and len(channels) > 1:
        raw = -sum(
            (n / total) * math.log(n / total) for n in channels.values()
        )
        entropy = raw / math.log(len(channels))

    repeats = sum(n - 1 for n in titles.values() if n > 1)

    return {
        "channels": len(channels),
        "top10_share": (
            sum(n for _, n in channels.most_common(10)) / total if total else 0.0
        ),
        "channel_entropy": round(entropy, 3),
        "rewatch_rate": round(repeats / len(events), 3) if events else 0.0,
    }


def analyse(watch_events: List[Dict]) -> Dict:
    """Pick the archetype whose axis deviates furthest from chance.

    Returns type, description, the evidence behind the choice, and supporting stats.
    """
    if not watch_events:
        return dict(EMPTY)

    candidates = [
        axis
        for axis in (
            _clock_axis(watch_events),
            _week_axis(watch_events),
            _calendar_axis(watch_events),
        )
        if axis is not None
    ]

    stats = _supporting_stats(watch_events)

    if not candidates:
        return {**BALANCED, "evidence": {"axis": None, "share": 0.0, "lift": 0.0},
                "stats": stats}

    best = max(candidates, key=lambda axis: axis["lift"])
    evidence = {
        "axis": best["axis"],
        "share": round(best["share"], 3),
        "lift": round(best["lift"], 2),
    }

    if best["lift"] < NOTABLE_LIFT:
        # Nothing stands out; naming a habit here would be inventing one.
        return {**BALANCED, "evidence": evidence, "stats": stats}

    return {
        "type": best["type"],
        "description": best["description"],
        "evidence": evidence,
        "stats": stats,
    }
