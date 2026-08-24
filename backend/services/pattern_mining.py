"""
Association-rule mining over watch history.

Every rule is scored the same way, so they can be ranked against each other:

    support    how many times it happened (guards against small-sample noise)
    confidence P(outcome | channel) -- how reliable the habit is
    lift       confidence / P(outcome) -- how much stronger than chance

Lift is what makes a rule interesting. "You watch this channel on Fridays 20% of the
time" sounds like a pattern until you notice 1/7 is 14%, so the lift is only 1.4.

On channel eligibility: the previous gate was max(10, len(watch_events) // 100), which
scaled with total watches. A user with 20,626 watches needed 206 on one channel to
qualify, leaving 4 eligible channels and zero patterns, while a lighter user with the
same habits got plenty. The gate is now an absolute floor -- it exists for statistical
validity, not to ration results by how much someone watches.
"""

from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
from typing import Dict, List, Optional, Set

# Minimum observations before a rule is trustworthy at all.
MIN_SUPPORT = 15
# How many of a user's channels are eligible. Top-N already restricts to their mainstays.
TOP_CHANNELS = 40
# Rules must be this much stronger than chance to be worth showing.
MIN_LIFT = 1.5
# A gap this long ends a viewing session.
SESSION_GAP_MINUTES = 60
# Sessions longer than this are almost always autoplay drift, not deliberate pairing.
MAX_SESSION_CHANNELS = 60
# A channel must span this many months before "seasonal" means anything. One watched
# only in April was never available to appear elsewhere, so its concentration carries
# no information -- that is a discovery, not a season.
MIN_SEASONAL_MONTHS = 3
# Cap per rule type so one kind cannot fill the card and hide the others.
MAX_PER_TYPE = 2

DAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
# name -> number of hours in the slot, used as the chance baseline
SLOTS = {
    "late night": (0, 5),
    "morning": (5, 12),
    "afternoon": (12, 17),
    "evening": (17, 21),
    "night": (21, 24),
}
SLOT_PHRASE = {
    "late night": "after midnight",
    "morning": "in the mornings",
    "afternoon": "in the afternoons",
    "evening": "in the evenings",
    "night": "late in the evening",
}


def top_channels(
    watch_events: List[Dict],
    limit: int = TOP_CHANNELS,
    min_support: int = MIN_SUPPORT,
) -> Set[str]:
    """The user's mainstay channels: most-watched, above an absolute support floor."""
    counts = Counter(
        e.get("channel_clean") for e in watch_events if e.get("channel_clean")
    )
    return {ch for ch, n in counts.most_common(limit) if n >= min_support}


def _slot_for(hour: int) -> Optional[str]:
    for name, (start, end) in SLOTS.items():
        if start <= hour < end:
            return name
    return None


def _rule(kind: str, count: int, confidence: float, lift: float, insight: str, **extra) -> Dict:
    return {
        "type": kind,
        "count": count,
        "confidence": confidence,
        "lift": lift,
        "insight": insight,
        **extra,
    }


def _association_rules(
    watch_events: List[Dict],
    channels: Set[str],
    key,
    label,
    phrase,
    kind: str,
    min_confidence: float,
    extra_field: str,
    min_distinct: int = 1,
) -> List[Dict]:
    """Shared channel x attribute mining, used for day, slot and month rules."""
    per_channel: Dict[str, Counter] = defaultdict(Counter)
    channel_total: Counter = Counter()
    attribute_total: Counter = Counter()

    for event in watch_events:
        value = key(event)
        if value is None:
            continue

        # The chance baseline is the share of ALL viewing with this attribute, not just
        # viewing on eligible channels. Restricting it to eligible channels compares a
        # channel partly against itself, which drives lift toward 1 and hides real
        # patterns whenever few channels qualify.
        attribute_total[value] += 1

        channel = event.get("channel_clean")
        if channel in channels:
            per_channel[channel][value] += 1
            channel_total[channel] += 1

    total = sum(attribute_total.values())
    if not total:
        return []

    rules = []
    for channel, values in per_channel.items():
        # Concentration only means something if the channel could have appeared
        # elsewhere; see MIN_SEASONAL_MONTHS.
        if len(values) < min_distinct:
            continue
        for value, count in values.items():
            if count < MIN_SUPPORT:
                continue
            confidence = count / channel_total[channel]
            baseline = attribute_total[value] / total
            lift = confidence / baseline if baseline else 0.0
            if confidence >= min_confidence and lift >= MIN_LIFT:
                rules.append(
                    _rule(
                        kind, count, confidence, lift,
                        phrase(channel, label(value), confidence),
                        channel=channel, **{extra_field: label(value)},
                    )
                )
    return rules


def channel_day_rules(watch_events: List[Dict], channels: Set[str]) -> List[Dict]:
    """Channels tied to a day of the week. Chance baseline is 1/7."""
    return _association_rules(
        watch_events, channels,
        key=lambda e: e.get("day_of_week"),
        label=lambda d: DAY_NAMES[d] if 0 <= d < 7 else "Unknown",
        phrase=lambda ch, day, conf: (
            f"You watch **{ch}** on **{day}s** ({int(conf * 100)}% of the time)"
        ),
        kind="channel_day", min_confidence=0.25, extra_field="day",
    )


def channel_slot_rules(watch_events: List[Dict], channels: Set[str]) -> List[Dict]:
    """Channels tied to a time of day. Baseline is the slot's real share of hours."""
    return _association_rules(
        watch_events, channels,
        key=lambda e: _slot_for(e["hour_local"]) if e.get("hour_local") is not None else None,
        label=lambda s: s,
        phrase=lambda ch, slot, conf: (
            f"**{ch}** is your go-to {SLOT_PHRASE.get(slot, slot)} "
            f"({int(conf * 100)}% of the time)"
        ),
        kind="channel_time", min_confidence=0.35, extra_field="slot",
    )


def seasonal_rules(watch_events: List[Dict], channels: Set[str]) -> List[Dict]:
    """Channels concentrated in one month -- sports seasons, exam periods, holidays."""
    return _association_rules(
        watch_events, channels,
        key=lambda e: e.get("month_local"),
        label=lambda m: MONTH_NAMES[m - 1] if 1 <= m <= 12 else "Unknown",
        phrase=lambda ch, month, conf: (
            f"**{ch}** is your **{month}** channel ({int(conf * 100)}% of it landed there)"
        ),
        kind="seasonal", min_confidence=0.35, extra_field="month",
        min_distinct=MIN_SEASONAL_MONTHS,
    )


def weekend_rule(watch_events: List[Dict], channels: Set[str]) -> Optional[Dict]:
    """Whether a mainstay channel skews to weekends. Chance baseline is 2/7."""
    weekend = Counter()
    totals = Counter()

    for event in watch_events:
        channel = event.get("channel_clean")
        day = event.get("day_of_week")
        if channel not in channels or day is None:
            continue
        totals[channel] += 1
        if day in (5, 6):
            weekend[channel] += 1

    best, best_lift, best_count = None, 0.0, 0
    for channel, total in totals.items():
        if total < MIN_SUPPORT:
            continue
        confidence = weekend[channel] / total
        lift = confidence / (2 / 7)
        if lift > best_lift:
            best, best_lift, best_count = channel, lift, weekend[channel]

    if best is None or best_lift < MIN_LIFT:
        return None

    confidence = best_count / totals[best]
    return _rule(
        "weekend", best_count, confidence, best_lift,
        f"**{best}** is your weekend channel ({int(confidence * 100)}% on Sat/Sun)",
        channel=best,
    )


def _sessions(watch_events: List[Dict]) -> List[List[str]]:
    """Channel sequences, split wherever viewing pauses for SESSION_GAP_MINUTES."""
    timed = []
    for event in watch_events:
        stamp = event.get("timestamp_local") or event.get("timestamp_utc")
        channel = event.get("channel_clean")
        if not stamp or not channel:
            continue
        try:
            timed.append((datetime.fromisoformat(stamp.replace("Z", "+00:00")), channel))
        except ValueError:
            continue

    if not timed:
        return []

    timed.sort(key=lambda pair: pair[0])
    sessions, current = [], [timed[0][1]]

    for index in range(1, len(timed)):
        gap = (timed[index][0] - timed[index - 1][0]).total_seconds() / 60
        if gap > SESSION_GAP_MINUTES:
            sessions.append(current)
            current = []
        current.append(timed[index][1])

    sessions.append(current)
    return sessions


def cooccurrence_rules(watch_events: List[Dict]) -> List[Dict]:
    """Channel pairs that show up in the same sitting far more often than chance.

    This is the classic market-basket rule -- sessions are baskets, channels are items.
    It surfaces groupings nobody configured: artists of a genre, a sport and its
    highlights reel.
    """
    sessions = _sessions(watch_events)
    if not sessions:
        return []

    total = len(sessions)
    appears = Counter()
    together = Counter()

    for session in sessions:
        unique = sorted(set(session))
        for channel in unique:
            appears[channel] += 1
        # Very long sessions are autoplay drift; every pair in them would look related.
        if len(unique) > MAX_SESSION_CHANNELS:
            continue
        for pair in combinations(unique, 2):
            together[pair] += 1

    rules = []
    for (first, second), count in together.items():
        if count < MIN_SUPPORT:
            continue
        expected = (appears[first] / total) * (appears[second] / total)
        lift = (count / total) / expected if expected else 0.0
        if lift < MIN_LIFT * 2:  # pairs are noisier, so demand a stronger signal
            continue
        confidence = max(count / appears[first], count / appears[second])
        rules.append(
            _rule(
                "cooccurrence", count, confidence, lift,
                f"**{first}** and **{second}** go together "
                f"({count} sessions, {lift:.1f}x more than chance)",
                channel_a=first, channel_b=second,
            )
        )
    return rules


def opener_rules(watch_events: List[Dict]) -> List[Dict]:
    """Channels that tend to start a viewing session -- the gateway into a run."""
    sessions = _sessions(watch_events)
    if not sessions:
        return []

    total = len(sessions)
    opens = Counter(session[0] for session in sessions if session)
    appears = Counter()
    for session in sessions:
        for channel in set(session):
            appears[channel] += 1

    # Chance baseline: across every channel-appearance, what share are openers? Each
    # session has exactly one opener out of however many channels it contains, so this
    # is 1/(average distinct channels per session). Dividing openers by sessions instead
    # would give 1.0 always, making every lift exactly 1.
    appearances = sum(appears.values())
    baseline = total / appearances if appearances else 0

    rules = []
    for channel, count in opens.items():
        if count < MIN_SUPPORT:
            continue
        confidence = count / appears[channel]
        lift = confidence / baseline if baseline else 0.0
        if lift < MIN_LIFT:
            continue
        rules.append(
            _rule(
                "opener", count, confidence, lift,
                f"**{channel}** is how you start a session "
                f"({count} times, {int(confidence * 100)}% of its sessions)",
                channel=channel,
            )
        )
    rules.sort(key=lambda r: r["count"], reverse=True)
    return rules


def find_patterns(watch_events: List[Dict], limit: int = 5) -> List[Dict]:
    """All rule types, ranked by confidence x lift, strongest first."""
    if not watch_events:
        return []

    channels = top_channels(watch_events)
    if not channels:
        return []

    rules: List[Dict] = []
    rules += channel_day_rules(watch_events, channels)
    rules += channel_slot_rules(watch_events, channels)
    rules += seasonal_rules(watch_events, channels)
    rules += cooccurrence_rules(watch_events)
    rules += opener_rules(watch_events)

    weekend = weekend_rule(watch_events, channels)
    if weekend:
        rules.append(weekend)

    rules.sort(key=lambda r: r["lift"] * r["confidence"], reverse=True)

    # Take the strongest rules, but never more than MAX_PER_TYPE of one kind: five
    # variations on "X is your April channel" reads as a malfunction, not a discovery.
    selected: List[Dict] = []
    per_type: Counter = Counter()
    for rule in rules:
        if per_type[rule["type"]] >= MAX_PER_TYPE:
            continue
        selected.append(rule)
        per_type[rule["type"]] += 1
        if len(selected) == limit:
            break

    return selected
