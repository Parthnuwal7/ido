"""
Takeout HTML -> raw cell records.

Knows the Takeout DOM template and nothing about YouTube semantics. Two consumers
(watch history and search history) share it, because both files use a byte-identical
cell template and differ only in how their fields map to Takeout JSON.

Why regex rather than an HTML parser: this is machine-generated output from a fixed
template with zero nesting variance across all 42,500 cells of the reference export,
and it is large (43 MB). Measured on the full file: this scanner 1.9 s, stdlib
html.parser 43 s, BeautifulSoup 2,968 s / 842 MB. If Google ever changes the template,
a tree parser would silently return wrong fields whereas this returns nothing -- which
the caller's drop-rate threshold turns into a loud failure.
"""

import re
from html import unescape
from typing import Iterator, List, Optional, Tuple

try:  # Python 3.8+
    from typing import TypedDict
except ImportError:  # pragma: no cover
    TypedDict = dict


class RawCell(TypedDict):
    """One activity cell, before any YouTube-specific interpretation."""

    product: str                        # "YouTube" | "YouTube Music"
    prefix: str                         # "Watched" | "Viewed" | "Searched for" | free text
    links: List[Tuple[str, str]]        # [(href, anchor_text), ...] in document order
    timestamp: Optional[str]            # raw wall-clock string, un-normalised
    is_ad: bool                         # "From Google Ads" present in the caption cell


# One cell runs from its outer-cell div through its caption cell. The caption is captured
# because ad markers live there, not in the body cell that holds title/channel/time.
_CELL = re.compile(
    r'<div class="outer-cell.*?mdl-typography--caption">(.*?)</div>', re.S
)
# The first body-1 cell only: the empty text-right cell's class continues past `body-1`.
_BODY = re.compile(r'mdl-typography--body-1">(.*?)</div>', re.S)
_HEADER = re.compile(r'mdl-typography--title">(.*?)<br>', re.S)
_HREF = re.compile(r'<a href="([^"]*)">(.*?)</a>', re.S)
_TAG = re.compile(r"<[^>]*>")

_AD_MARKER = "From Google Ads"


def _timestamp_from(body: str) -> Optional[str]:
    """The timestamp is the last tag-free text segment in the body cell.

    Deliberately format-agnostic: Takeout renders dates in the account's locale, and
    deciding whether a string is a parseable date belongs to takeout_time, not here.
    """
    for segment in reversed(body.split("<br>")):
        if "<" in segment:
            continue
        text = unescape(segment).replace("\xa0", " ").strip()
        if text:
            return segment.strip()
    return None


def scan(html: str) -> Iterator[RawCell]:
    """Yield one RawCell per activity cell, lazily, in document order.

    Cells that carry no body cell are skipped rather than raising, so a single
    malformed cell cannot fail an entire history file.
    """
    if not html:
        return

    for match in _CELL.finditer(html):
        block, caption = match.group(0), match.group(1)

        body_match = _BODY.search(block)
        if not body_match:
            continue
        body = body_match.group(1)

        header = _HEADER.search(block)
        prefix = unescape(body.split("<", 1)[0]).replace("\xa0", " ").strip()

        yield RawCell(
            product=unescape(header.group(1)).strip() if header else "",
            prefix=prefix,
            links=[
                (unescape(href), unescape(_TAG.sub("", text)).strip())
                for href, text in _HREF.findall(body)
            ],
            timestamp=_timestamp_from(body),
            is_ad=_AD_MARKER in caption,
        )
