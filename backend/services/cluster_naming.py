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

# Topics so broad they describe nearly every channel; they crowd out the useful ones.
GENERIC_TOPICS = {
    "Music", "Entertainment", "Lifestyle (sociology)", "Society", "Hobby",
    "Knowledge", "Film", "Performing arts",
}

# Ignored when deciding whether two names are really the same.
FILLER_WORDS = {"and", "the", "of", "a", "an", "your", "music"}

SYSTEM_PROMPT = (
    "You name groups of YouTube channels. For each numbered group you get the channel "
    "names, and sometimes the topic categories YouTube assigns them.\n\n"
    "The channel names are the real signal. YouTube's topic categories are extremely "
    "coarse -- Bollywood playback singers, K-pop and Western EDM all come back as "
    "'Pop music, Music, Electronic music' -- so treat them as a weak hint and never "
    "just echo them back.\n\n"
    "Name each group for what those specific channels actually are: "
    "'Bollywood Playback' rather than 'Asian, Pop, Music'; 'IPL Cricket' rather than "
    "'Sport, Lifestyle'; 'Indian News' rather than 'Entertainment, Society'.\n\n"
    "Every name must be DISTINCT from the others -- two groups sharing a name, or the "
    "same words in a different order, makes the list unreadable. If two groups look "
    "similar, find what separates them.\n\n"
    "Reply with JSON only: an object mapping each group number (as a string) to a name "
    "of at most four words, e.g. {\"0\": \"IPL Cricket\"}. No prose, no code fences."
)


def channel_label(channels: List[str]) -> str:
    """The always-correct fallback: the cluster's own biggest channels."""
    return " · ".join(channels[:3])


def _prompt(clusters: List[Dict], facts: Dict[str, Dict]) -> str:
    """One line per group: channel names first, topics as a trailing hint.

    Topics are collected per cluster but kept short. Deduplicating them across a
    whole cluster is what flattened every music world into the same three words,
    so the channel names lead and the taxonomy only ever supplements them.
    """
    lines = []
    for cluster in clusters:
        names = cluster["channels"][:MAX_CHANNELS_SENT]
        topics = []
        for name in names:
            for topic in (facts.get(name) or {}).get("topics", []):
                if topic not in topics and topic not in GENERIC_TOPICS:
                    topics.append(topic)
        line = f"{cluster['index']}: {', '.join(names)}"
        if topics:
            line += f"  (hint: {', '.join(topics[:4])})"
        lines.append(line)
    return "\n".join(lines)


def _normalise(name: str) -> str:
    """A comparison key that treats reorderings as the same name.

    "Pop, Electronic, Music" and "Electronic, Pop, Music" are not two names.
    """
    words = re.findall(r"[a-z]+", name.lower())
    return " ".join(sorted(w for w in words if w not in FILLER_WORDS))


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
    seen: set = set()

    for key, value in (raw or {}).items():
        try:
            index = int(key)
        except (TypeError, ValueError):
            continue
        if index not in valid or not isinstance(value, str) or not value.strip():
            continue

        name = value.strip()[:MAX_NAME_LENGTH]
        signature = _normalise(name)

        # A repeated name is worse than none: two worlds labelled the same cannot be
        # told apart, and the channel-label fallback at least stays true. Drop the
        # collision rather than show it.
        if not signature or signature in seen:
            continue

        seen.add(signature)
        names[index] = name

    return names
