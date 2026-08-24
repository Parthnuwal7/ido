"""
Data Portability archive -> Wrapped cards.

Downloads a completed export, runs it through the same ingest as an uploaded ZIP, tops
up subscriptions from the YouTube Data API (they are not in the archive), and generates
cards. Nothing is retained: the archive is streamed to a temporary file and deleted in a
finally block, and the access token is used and dropped.
"""

import os
import tempfile
from typing import Dict, List, Optional

from services import portability_client
from services.portability_client import PortabilityError
from services.preprocess_service import preprocess_subscriptions
from services.takeout_ingest import ingest_zip
from services.wrapped_service import generate_wrapped_cards


def _add_subscriptions(oauth_token, timezone, client, events, stats) -> None:
    """Fill in subscriptions from the Data API when the archive has none.

    Subscriptions come from the *oauth* grant (youtube.readonly) -- the portability
    token cannot read them, and the archive does not contain them.

    Failures here are swallowed deliberately: subscriptions drive one card out of
    nineteen, and losing that card is a far better outcome than losing the whole
    Wrapped because a scope was declined.
    """
    if not oauth_token:
        print("[WARN] No oauth token; skipping the subscriptions card")
        return

    try:
        subscriptions = client.fetch_subscriptions(oauth_token)
    except PortabilityError as exc:
        print(f"[WARN] Could not read subscriptions: {exc}")
        return

    if not subscriptions:
        return

    csv_text = client.subscriptions_to_csv(subscriptions)
    subscribe_events = preprocess_subscriptions(csv_text, timezone)

    events.extend(subscribe_events)
    stats["total_subscribe"] = len(subscribe_events)
    stats["total_events"] = len(events)


def build_wrapped(
    access_token: str,
    urls: List[str],
    timezone: str = "UTC",
    year: Optional[int] = None,
    oauth_token: Optional[str] = None,
    client=portability_client,
) -> Dict:
    """Turn a completed export into Wrapped cards.

    Args:
        access_token: the browser's Google access token (portability grant), used for
            this call only.
        urls: signed download URLs from the completed job.
        timezone: IANA name the user selected.
        year: calendar year to cover; defaults as elsewhere in the pipeline.
        oauth_token: second grant (openid + youtube.readonly), used only to top up
            subscriptions. May be None; the subscriptions card is skipped then.

    Raises:
        PortabilityError: downloading the archive failed.
    """
    handle, archive_path = tempfile.mkstemp(suffix=".zip", prefix="ido-portability-")
    os.close(handle)

    try:
        client.download_archive(urls, archive_path)
        print(f"[Portability] Archive downloaded ({os.path.getsize(archive_path):,} bytes)")

        with open(archive_path, "rb") as archive:
            result = ingest_zip(archive, timezone, year=year)

        print(
            f"[Portability] Ingested {result.stats['total_events']} events "
            f"({result.stats['total_watch']} watch, {result.stats['total_search']} search, "
            f"{result.stats['total_subscribe']} subscribe) for year {result.year}"
        )

        if not result.stats.get("total_subscribe"):
            _add_subscriptions(oauth_token, timezone, client, result.events, result.stats)

        cards = generate_wrapped_cards(result.events, result.stats)
        print(f"[Portability] Generated {len(cards)} card sections")

        metadata = cards.setdefault("metadata", {})
        metadata["source"] = "data_portability"
        metadata["year"] = result.year
        metadata["years_available"] = result.years_available
        if result.report:
            metadata["parse_report"] = result.report

        return cards

    finally:
        # The user's export must never be left behind, including on failure.
        if os.path.exists(archive_path):
            os.remove(archive_path)
