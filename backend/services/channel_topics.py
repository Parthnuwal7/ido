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
from typing import Dict, List, Optional

import requests

YOUTUBE_API = "https://www.googleapis.com/youtube/v3/channels"
BATCH_SIZE = 50          # the API's per-request id limit
TIMEOUT = 15

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


def fetch(
    channel_ids: List[str],
    api_key: Optional[str],
    session=None,
) -> Optional[Dict[str, Dict]]:
    """Title, topics and subscriber count per channel id.

    Returns None when no key is configured or the API cannot be reached -- both are
    ordinary states that degrade the Wrapped rather than failing it.
    """
    if not api_key:
        return None
    if not channel_ids:
        return {}

    client = session if session is not None else requests
    facts: Dict[str, Dict] = {}

    for start in range(0, len(channel_ids), BATCH_SIZE):
        batch = channel_ids[start:start + BATCH_SIZE]
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
