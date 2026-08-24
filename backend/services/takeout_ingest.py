"""
Takeout ZIP -> normalized events, stats and a parse report.

Extracted from wrapped_routes.process_zip_in_memory so the ingest path can be tested
without FastAPI and so the route stays thin.

Handles both export formats. Google Takeout exports history as HTML by default; JSON
requires the user to open "Multiple formats" and switch it. JSON is preferred whenever
present because it is lossless and carries no parsing risk, with HTML converted to the
same entry shape so exactly one downstream path exists.
"""

import io
import json
import os
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from services import channel_topics, cluster_naming
from services.history_locator import HTML, HistoryFile, find_history
from services.preprocess_service import (
    preprocess_search_entries,
    preprocess_subscriptions,
    preprocess_watch_entries,
)
from services.takeout_html_mapper import to_search_entries, to_watch_entries
from services.takeout_html_scanner import scan
from services.wrapped_year import partition_by_year, select_year

# Below this share of cells surviving the parse, fail rather than return partial data.
# A systematic format mismatch (an unhandled export locale) shows up as a high drop
# rate, and a Wrapped built from a fraction of someone's history looks entirely normal
# -- which makes silent partial output worse than an honest error.
MIN_YIELD = 0.8


class HistoryParseError(Exception):
    """Raised when too few cells survived parsing to trust the result."""


@dataclass
class IngestResult:
    events: List[Dict] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)
    report: Dict = field(default_factory=dict)
    year: Optional[int] = None
    years_available: List[int] = field(default_factory=list)


def _empty_stats() -> Dict:
    return {
        "total_events": 0,
        "total_watch": 0,
        "total_search": 0,
        "total_subscribe": 0,
        "language_breakdown": {"english": 0, "hindi": 0, "hinglish": 0, "unknown": 0},
    }


def _read(zf: zipfile.ZipFile, member: str) -> str:
    with zf.open(member) as handle:
        return handle.read().decode("utf-8", errors="replace")


def _check_yield(report: Dict, label: str) -> None:
    seen = report["cells_seen"]
    if not seen:
        return

    if report["entries_emitted"] / seen >= MIN_YIELD:
        return

    top = max(report["dropped"].items(), key=lambda kv: kv[1], default=("UNKNOWN", 0))
    raise HistoryParseError(
        f"Only {report['entries_emitted']} of {seen} {label} entries could be read "
        f"(most common reason: {top[0]}). This usually means the export uses a date "
        f"format we do not handle yet."
    )


def _json_entries(content: str) -> List[Dict]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _entries(
    zf: zipfile.ZipFile,
    found: Optional[HistoryFile],
    tz: str,
    report: Dict,
    mapper,
    label: str,
) -> List[Dict]:
    """Takeout JSON entries from either export format.

    Both formats converge on the same entry shape here, so year filtering and
    preprocessing downstream have exactly one code path to handle.
    """
    if not found:
        return []

    content = _read(zf, found.member)
    if found.format != HTML:
        return _json_entries(content)

    entries, parse_report = mapper(scan(content), tz)
    report[label] = parse_report
    _check_yield(parse_report, f"{label} history")
    return entries


def ingest_zip(
    source: Union[bytes, io.IOBase],
    timezone: str = "UTC",
    year: Optional[int] = None,
) -> IngestResult:
    """Read a Takeout ZIP and return one year's events, stats and a parse report.

    Entries are filtered to the chosen year *before* preprocessing, so text cleaning,
    language detection and timezone enrichment only run on entries that reach a card.

    Args:
        source: ZIP bytes, or a file object. Prefer a file object -- FastAPI already
            spools large uploads to disk, and passing the handle keeps a multi-hundred-MB
            body off the heap.
        timezone: IANA name the user selected, e.g. "Asia/Kolkata".
        year: calendar year to cover. Defaults to the current year, falling back to the
            most recent year with watch history.

    Raises:
        HistoryParseError: if too few cells parsed to trust the output.
    """
    stats = _empty_stats()
    report: Dict = {}
    events: List[Dict] = []

    handle = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source

    with zipfile.ZipFile(handle) as zf:
        found = find_history(zf.namelist())

        watch_entries = _entries(
            zf, found.watch, timezone, report, to_watch_entries, "watch"
        )
        search_entries = _entries(
            zf, found.search, timezone, report, to_search_entries, "search"
        )

        buckets = partition_by_year(watch_entries, timezone)
        years_available = sorted(y for y in buckets if y is not None)
        selected = select_year(years_available, requested=year)

        if selected is not None:
            watch_entries = buckets.get(selected, [])
            search_entries = partition_by_year(search_entries, timezone).get(selected, [])

        watch = preprocess_watch_entries(watch_entries, timezone)
        events.extend(watch)
        stats["total_watch"] = len(watch)

        search = preprocess_search_entries(search_entries, timezone)
        events.extend(search)
        stats["total_search"] = len(search)

        # subscriptions.csv carries no date column, so subscriptions are exempt from
        # year filtering -- otherwise the ghost-subscriptions card empties out.
        if found.subscriptions:
            subs = preprocess_subscriptions(_read(zf, found.subscriptions), timezone)
            events.extend(subs)
            stats["total_subscribe"] = len(subs)

    for event in events:
        language = event.get("language_type", "unknown")
        if language in stats["language_breakdown"]:
            stats["language_breakdown"][language] += 1

    stats["total_events"] = len(events)
    stats["year"] = selected

    return IngestResult(
        events=events,
        stats=stats,
        report=report,
        year=selected,
        years_available=years_available,
    )


def build_enrichment(watch_events, interest, consented: bool) -> Dict:
    """Optional network enrichment for the taste cards.

    Returns {"names": {...}, "facts": {...} | None}. Every failure path returns the
    empty form: enrichment makes cards better when it works and is invisible when it
    does not, but it can never fail a Wrapped.

    Facts come back from Google keyed by channel id, but every card looks them up by
    channel_clean, so the mapping is translated back before returning.
    """
    empty = {"names": {}, "facts": None}
    if interest is None:
        return empty

    try:
        ids_by_channel = {}
        for event in watch_events:
            channel = event.get("channel_clean")
            if channel in interest.cluster_of and channel not in ids_by_channel:
                channel_id = channel_topics.channel_id_from_url(event.get("channel_url"))
                if channel_id:
                    ids_by_channel[channel] = channel_id

        by_id = channel_topics.fetch(
            list(ids_by_channel.values()), os.getenv("YOUTUBE_API_KEY")
        )
        facts = None
        if by_id:
            facts = {
                channel: by_id[channel_id]
                for channel, channel_id in ids_by_channel.items()
                if channel_id in by_id
            }

        # Checked here as well as inside name_clusters. The consent gate guards the one
        # place user-derived data leaves the server, so it gets two independent guards
        # rather than one -- neither layer should be the only thing standing between a
        # user's channel names and a third party.
        names = {}
        if consented:
            names = cluster_naming.name_clusters(
                interest.clusters, facts, os.getenv("OPENROUTER_API_KEY"), consented
            )

        return {"names": names or {}, "facts": facts}
    except Exception as exc:  # noqa: BLE001 - enrichment is never critical
        print(f"[WARN] Enrichment skipped: {exc}")
        return empty
