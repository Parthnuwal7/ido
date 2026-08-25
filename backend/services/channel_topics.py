"""
Channel facts from the YouTube Data API.

The only place we ask Google about channels. One `channels.list` request costs 1 quota
unit and accepts 50 ids, against a 10,000/day default -- naming six clusters needs one
request, and subscriber counts for a whole clustered vocabulary needs about six.
`part=snippet,topicDetails,statistics` returns all of it at that same single cost.

Nothing here is on the critical path. No key, a failed request, or a network error all
return None, and the caller falls back to channel-name labels and hides niche_meter.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import requests

YOUTUBE_API = "https://www.googleapis.com/youtube/v3/channels"
BATCH_SIZE = 50          # the API's per-request id limit
TIMEOUT = 15
# Batches are independent, so they go out together. A 284-channel vocabulary is six
# round-trips: ~4.0s one after another against ~0.7s in parallel. Capped so a large
# history cannot open an unbounded number of sockets.
MAX_PARALLEL = 6

_CHANNEL_URL = re.compile(r"/channel/(UC[\w-]{22})")


def channel_id_from_url(url: Optional[str]) -> Optional[str]:
    """The UC... id inside a Takeout channel URL, or None."""
    if not url:
        return None
    match = _CHANNEL_URL.search(url)
    return match.group(1) if match else None


def _topic_name(topic_url: str) -> str:
    """'https://en.wikipedia.org/wiki/Electronic_music' -> 'Electronic music'."""
    return topic_url.rstrip("/").rsplit("/", 1)[-1].replace("_", " ")


def _fetch_batch(batch: List[str], api_key: str, client) -> Optional[Dict[str, Dict]]:
    """One channels.list request. None on any failure -- the caller aborts as a whole."""
    try:
        response = client.get(
            YOUTUBE_API,
            params={
                "part": "snippet,topicDetails,statistics",
                "id": ",".join(batch),
                "key": api_key,
                "maxResults": BATCH_SIZE,
            },
            timeout=TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001 - never raise into the pipeline
        print(f"[WARN] Channel topics unavailable: {exc}")
        return None

    if getattr(response, "status_code", 500) >= 400:
        print(f"[WARN] Channel topics request failed ({response.status_code})")
        return None

    try:
        body = response.json() or {}
    except ValueError:
        return None

    facts: Dict[str, Dict] = {}
    for entry in body.get("items", []):
        subscribers = (entry.get("statistics") or {}).get("subscriberCount")
        try:
            subscribers = int(subscribers) if subscribers is not None else None
        except (TypeError, ValueError):
            subscribers = None

        topics = (entry.get("topicDetails") or {}).get("topicCategories") or []
        facts[entry.get("id", "")] = {
            "title": (entry.get("snippet") or {}).get("title", ""),
            "topics": [_topic_name(t) for t in topics],
            "subscribers": subscribers,
        }
    return facts


def fetch(
    channel_ids: List[str],
    api_key: Optional[str],
    session=None,
) -> Optional[Dict[str, Dict]]:
    """Title, topics and subscriber count per channel id.

    Batches go out concurrently: they are independent requests and the work is entirely
    network wait, so six round-trips cost about one. Returns None when no key is
    configured or any batch fails -- both are ordinary states that degrade the Wrapped
    rather than failing it, and a partial result would silently under-report.
    """
    if not api_key:
        return None
    if not channel_ids:
        return {}

    client = session if session is not None else requests
    batches = [
        channel_ids[start:start + BATCH_SIZE]
        for start in range(0, len(channel_ids), BATCH_SIZE)
    ]

    if len(batches) == 1:
        return _fetch_batch(batches[0], api_key, client)

    with ThreadPoolExecutor(max_workers=min(len(batches), MAX_PARALLEL)) as pool:
        results = list(pool.map(lambda b: _fetch_batch(b, api_key, client), batches))

    if any(result is None for result in results):
        return None

    facts: Dict[str, Dict] = {}
    for result in results:
        facts.update(result)
    return facts
