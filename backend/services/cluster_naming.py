"""
Human names for taste worlds, via one OpenRouter call.

Naming clusters from video titles was tried and rejected -- TF-IDF over titles produced
usable labels about a third of the time and hashtag debris the rest, and a confidently
wrong label is worse than none because the viewer cannot tell which they got. So the
model is given Google's own topic categories as facts and asked to summarise them.

Privacy: this is the only place user-derived data leaves the server, so it is gated on
explicit consent and sends the minimum that can work -- up to five channel names per
cluster and their topic categories. Never watch history, timestamps, video titles, or
anything identifying. Any failure returns {} and the caller uses channel labels.
"""

import json
import os
import re
from typing import Dict, List, Optional

import requests

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"
MAX_CHANNELS_SENT = 5      # enough to characterise a cluster, no more than needed
MAX_NAME_LENGTH = 40
TIMEOUT = 30

SYSTEM_PROMPT = (
    "You name groups of YouTube channels. For each numbered group you are given some "
    "channel names and the topic categories YouTube assigns them. Reply with JSON only: "
    "an object mapping each group number (as a string) to a short human name of at most "
    "four words, for example {\"0\": \"IPL Cricket\"}. Use the topics given; do not "
    "invent facts. No prose, no code fences."
)


def channel_label(channels: List[str]) -> str:
    """The always-correct fallback: the cluster's own biggest channels."""
    return " · ".join(channels[:3])


def _prompt(clusters: List[Dict], facts: Dict[str, Dict]) -> str:
    lines = []
    for cluster in clusters:
        names = cluster["channels"][:MAX_CHANNELS_SENT]
        topics = []
        for name in names:
            for topic in (facts.get(name) or {}).get("topics", []):
                if topic not in topics:
                    topics.append(topic)
        line = f"{cluster['index']}: channels = {', '.join(names)}"
        if topics:
            line += f"; topics = {', '.join(topics[:6])}"
        lines.append(line)
    return "\n".join(lines)


def name_clusters(
    clusters: List[Dict],
    facts: Optional[Dict[str, Dict]],
    api_key: Optional[str],
    consented: bool,
    session=None,
    model: Optional[str] = None,
) -> Dict[int, str]:
    """Short names per cluster index, or {} to signal "use channel labels".

    Consent gates the request itself: when `consented` is False no call is made at all,
    rather than a call whose result is thrown away.
    """
    if not consented or not api_key or not clusters:
        return {}

    client = session if session is not None else requests
    payload = {
        "model": model or os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _prompt(clusters, facts or {})},
        ],
    }

    try:
        response = client.post(
            OPENROUTER_API,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001 - never raise into the pipeline
        print(f"[WARN] Cluster naming unavailable: {exc}")
        return {}

    if getattr(response, "status_code", 500) >= 400:
        print(f"[WARN] Cluster naming failed ({response.status_code})")
        return {}

    try:
        body = response.json() or {}
        content = body["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return {}

    # Models sometimes wrap JSON in prose or fences; take the outermost object.
    match = re.search(r"\{.*\}", content, re.S)
    if not match:
        return {}
    try:
        raw = json.loads(match.group(0))
    except ValueError:
        return {}

    names: Dict[int, str] = {}
    valid = {c["index"] for c in clusters}
    for key, value in (raw or {}).items():
        try:
            index = int(key)
        except (TypeError, ValueError):
            continue
        if index in valid and isinstance(value, str) and value.strip():
            names[index] = value.strip()[:MAX_NAME_LENGTH]
    return names
