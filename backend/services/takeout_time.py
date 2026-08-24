"""
Takeout HTML timestamp resolution.

Google Takeout's HTML export renders timestamps as wall-clock time in the exporter's
Google-account timezone, tagged with a timezone abbreviation:

    Aug 21, 2026, 12:13:55 PM IST

The JSON export instead gives a true UTC instant. The rest of the pipeline expects UTC,
because enrich_event_with_local_time() shifts UTC -> the timezone the user selected. So
this module has to invert the render: wall clock -> UTC.

Timezone abbreviations are not machine-resolvable on their own (IST is India +5:30,
Israel +2/+3, and Irish Summer +1; CST is US Central, China, and Cuba). So the user's
selected timezone is the authority and the abbreviation is used as a checksum. That
also makes DST fall-back exact: EST vs EDT tells us which side of the repeated hour a
timestamp belongs to, which the wall clock alone cannot express.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytz

# Drop reasons
BAD_FORMAT = "BAD_FORMAT"
NONEXISTENT = "NONEXISTENT"
UNKNOWN_TZ = "UNKNOWN_TZ"

# Warnings (entry is still usable)
TZ_MISMATCH = "TZ_MISMATCH"

# Takeout renders dates in the account's locale. Only en-US is verified against a real
# export, so only en-US is implemented. Other locales surface as BAD_FORMAT in the parse
# report, and each confirmed one gets added here with a fixture rather than guessed at.
_EN_US = re.compile(
    r"^([A-Z][a-z]{2}) (\d{1,2}), (\d{4}), "
    r"(\d{1,2}):(\d{2}):(\d{2}) ([AP])M ([A-Za-z]{2,5})$"
)

_MONTHS = {
    m: i
    for i, m in enumerate(
        "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), start=1
    )
}

# Consulted only when the abbreviation disagrees with the user's selected timezone --
# i.e. they exported in one zone and are viewing in another. Ambiguous abbreviations are
# resolved to their most common interpretation in YouTube exports and always flagged
# TZ_MISMATCH, because salvaging the history with a warning beats dropping all of it.
_FALLBACK_OFFSETS = {
    "UTC": 0, "GMT": 0,
    "IST": 330,     # India (also Israel +120, Irish Summer +60)
    "PKT": 300, "GST": 240, "MSK": 180,
    "CET": 60, "CEST": 120, "EET": 120, "EEST": 180, "WET": 0, "WEST": 60,
    "BST": 60,      # British Summer (also Bangladesh +360)
    "EST": -300, "EDT": -240, "CST": -360, "CDT": -300,  # CST also China +480
    "MST": -420, "MDT": -360, "PST": -480, "PDT": -420,
    "AKST": -540, "AKDT": -480, "HST": -600,
    "JST": 540, "KST": 540, "HKT": 480, "SGT": 480, "WIB": 420,
    "AEST": 600, "AEDT": 660, "ACST": 570, "ACDT": 630, "AWST": 480,
    "NZST": 720, "NZDT": 780,
    "BRT": -180, "ART": -180, "CLT": -240,
}


@dataclass(frozen=True)
class TimeResult:
    """Either a resolved UTC instant, or a reason the entry has to be dropped."""

    utc: Optional[datetime] = None
    reason: Optional[str] = None
    warning: Optional[str] = None


def _normalise(raw: str) -> str:
    """Takeout uses U+202F before the meridiem and U+00A0 elsewhere."""
    return re.sub(r"\s+", " ", raw.replace(" ", " ").replace("\xa0", " ")).strip()


def _from_fallback_table(naive: datetime, abbrev: str) -> TimeResult:
    minutes = _FALLBACK_OFFSETS.get(abbrev.upper())
    if minutes is None:
        return TimeResult(reason=UNKNOWN_TZ)
    fixed = timezone(timedelta(minutes=minutes))
    return TimeResult(
        utc=naive.replace(tzinfo=fixed).astimezone(pytz.UTC), warning=TZ_MISMATCH
    )


def to_utc(raw: Optional[str], user_tz: str) -> TimeResult:
    """Convert a Takeout HTML wall-clock string to a UTC instant.

    Args:
        raw: e.g. "Aug 21, 2026, 12:13:55 PM IST" (may contain U+202F / U+00A0)
        user_tz: IANA name the user selected, e.g. "Asia/Kolkata"

    Returns:
        TimeResult with .utc set, or .reason set to one of BAD_FORMAT / NONEXISTENT /
        UNKNOWN_TZ. .warning is TZ_MISMATCH when the abbreviation disagreed with user_tz
        and the fallback table was used.
    """
    if not raw:
        return TimeResult(reason=BAD_FORMAT)

    match = _EN_US.match(_normalise(raw))
    if not match:
        return TimeResult(reason=BAD_FORMAT)

    mon, day, year, hour, minute, second, meridiem, abbrev = match.groups()
    if mon not in _MONTHS:
        return TimeResult(reason=BAD_FORMAT)

    hour = int(hour) % 12 + (12 if meridiem == "P" else 0)
    try:
        naive = datetime(
            int(year), _MONTHS[mon], int(day), hour, int(minute), int(second)
        )
    except ValueError:
        return TimeResult(reason=BAD_FORMAT)

    try:
        tz = pytz.timezone(user_tz)
    except pytz.UnknownTimeZoneError:
        return _from_fallback_table(naive, abbrev)

    try:
        localised = tz.localize(naive, is_dst=None)
    except pytz.exceptions.AmbiguousTimeError:
        # DST fall-back: this wall clock happened twice. The abbreviation says which.
        for is_dst in (True, False):
            candidate = tz.localize(naive, is_dst=is_dst)
            if candidate.strftime("%Z") == abbrev:
                return TimeResult(utc=candidate.astimezone(pytz.UTC))
        return _from_fallback_table(naive, abbrev)
    except pytz.exceptions.NonExistentTimeError:
        # DST spring-forward gap: this wall clock never happened. Don't invent one.
        return TimeResult(reason=NONEXISTENT)

    if localised.strftime("%Z") == abbrev:
        return TimeResult(utc=localised.astimezone(pytz.UTC))

    return _from_fallback_table(naive, abbrev)
