"""
The seeded demo Wrapped.

Seeds a real Takeout archive into the system and processes it exactly as an upload is
processed: locate the members, detect the format, run the HTML connector, resolve
timestamps, filter to the year, preprocess, generate cards. Nothing is short-circuited.

That matters because a demo built from pre-parsed entries would keep working after the
connector broke -- it would be showcasing a path that no longer runs. Going through
ingest_zip means the demo fails loudly with everything else, and doubles as a live smoke
test of the whole chain.

See scripts/generate_demo_data.py for how the archive is built and which insights it
deliberately plants.
"""

import os
from functools import lru_cache
from typing import Dict

from services.takeout_ingest import ingest_zip
from services.wrapped_service import generate_wrapped_cards

DEMO_YEAR = 2025
# The archive's timestamps are rendered in UTC and tagged UTC, so reading it as UTC
# round-trips exactly and the planted clock-hour signals land where the generator put them.
DEMO_TIMEZONE = "UTC"

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures")
DEMO_TAKEOUT = os.path.join(FIXTURES, "demo_takeout.zip")


@lru_cache(maxsize=1)
def load_demo_cards() -> Dict:
    """Process the seeded Takeout archive into Wrapped cards, once per process.

    Cached because the archive is immutable at runtime; there is no reason to re-parse
    2,500 HTML cells for every visitor to the demo page.
    """
    with open(DEMO_TAKEOUT, "rb") as archive:
        result = ingest_zip(archive, DEMO_TIMEZONE, year=DEMO_YEAR)

    cards = generate_wrapped_cards(result.events, result.stats)

    metadata = cards.setdefault("metadata", {})
    metadata["demo"] = True
    metadata["year"] = result.year
    metadata["years_available"] = result.years_available
    if result.report:
        metadata["parse_report"] = result.report

    return cards


def demo_archive_bytes() -> bytes:
    """The seeded Takeout archive, for the browser to upload as if it were its own.

    Serving the file rather than the finished cards means the demo travels the exact
    same path as a real export -- member location, format detection, the HTML
    connector, timestamp resolution, year filtering, preprocessing, enrichment -- so
    it cannot keep working after the parts it showcases have broken.
    """
    with open(DEMO_TAKEOUT, "rb") as archive:
        return archive.read()
