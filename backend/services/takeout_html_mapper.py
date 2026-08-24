"""
Raw Takeout HTML cells -> Takeout JSON entry dicts.

The contract is fidelity, not judgement: emit the shape Google's JSON export produces so
preprocess_watch_history() and its is_google_ads() / is_youtube_post() filters run
unchanged. Anything that looks like a product decision -- separating YouTube Music,
dropping empty-titled private videos -- belongs downstream, where it applies to the JSON
path identically.

Fields emitted are those the pipeline consumes, plus `header` for fidelity. A real JSON
export also carries `products` and `activityControls`; those are deliberately not
invented here, and the golden-master diff against a real JSON export is what will
confirm whether they matter.
"""

from typing import Dict, Iterable, List, Optional, Tuple

from services.takeout_html_scanner import RawCell
from services.takeout_time import to_utc

try:  # Python 3.8+
    from typing import TypedDict
except ImportError:  # pragma: no cover
    TypedDict = dict

NO_TIMESTAMP = "NO_TIMESTAMP"

_AD_DETAIL = [{"name": "From Google Ads"}]


class ParseReport(TypedDict):
    """Observability for a single history file: what was seen, kept, and lost."""

    cells_seen: int
    entries_emitted: int
    dropped: Dict[str, int]
    warnings: Dict[str, int]


def _new_report() -> ParseReport:
    return ParseReport(cells_seen=0, entries_emitted=0, dropped={}, warnings={})


def _bump(counter: Dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _resolve_time(cell: RawCell, user_tz: str, report: ParseReport) -> Optional[str]:
    """Wall clock -> ISO-8601 UTC, or None with the reason recorded."""
    if not cell["timestamp"]:
        _bump(report["dropped"], NO_TIMESTAMP)
        return None

    result = to_utc(cell["timestamp"], user_tz)
    if result.reason:
        _bump(report["dropped"], result.reason)
        return None
    if result.warning:
        _bump(report["warnings"], result.warning)

    return result.utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _identity(cell: RawCell) -> Dict:
    """The header/title/titleUrl prefix shared by watch and search entries.

    The title is always `"<prefix> <anchor text>"`, which reproduces the JSON export for
    both resolvable titles and private/deleted videos -- Google renders the raw URL as
    anchor text in the latter case, giving `"Watched https://..."` exactly as JSON does.

    Callers append the remaining keys in JSON-export order.
    """
    entry: Dict = {"header": cell["product"] or "YouTube"}

    if cell["links"]:
        url, text = cell["links"][0]
        entry["title"] = f"{cell['prefix']} {text}".strip()
        entry["titleUrl"] = url
    else:
        entry["title"] = cell["prefix"]

    return entry


def to_watch_entries(
    cells: Iterable[RawCell], user_tz: str
) -> Tuple[List[Dict], ParseReport]:
    """Map watch-history cells to Takeout JSON entries."""
    entries: List[Dict] = []
    report = _new_report()

    for cell in cells:
        report["cells_seen"] += 1

        time_str = _resolve_time(cell, user_tz, report)
        if time_str is None:
            continue

        entry = _identity(cell)

        # A second link is the channel. Its absence is meaningful -- private/deleted
        # videos and most ads have none -- so the key is omitted, as JSON omits it.
        if len(cell["links"]) > 1:
            url, name = cell["links"][1]
            entry["subtitles"] = [{"name": name, "url": url}]

        entry["time"] = time_str

        if cell["is_ad"]:
            entry["details"] = _AD_DETAIL

        entries.append(entry)
        report["entries_emitted"] += 1

    return entries, report


def to_search_entries(
    cells: Iterable[RawCell], user_tz: str
) -> Tuple[List[Dict], ParseReport]:
    """Map search-history cells to Takeout JSON entries.

    Search entries never carry a channel, so they are the base entry unchanged.
    """
    entries: List[Dict] = []
    report = _new_report()

    for cell in cells:
        report["cells_seen"] += 1

        time_str = _resolve_time(cell, user_tz, report)
        if time_str is None:
            continue

        entries.append({**_identity(cell), "time": time_str})
        report["entries_emitted"] += 1

    return entries, report
