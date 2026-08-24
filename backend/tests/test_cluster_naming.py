"""Tests for cluster_naming: the LLM seam.

Two things are load-bearing here and both are tested: consent gates the call entirely
(not just its result), and only channel names plus topics ever leave -- never watch
history, timestamps, titles, or identity.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.cluster_naming import (  # noqa: E402
    DEFAULT_MODEL,
    MAX_CHANNELS_SENT,
    channel_label,
    name_clusters,
)

KEY = "fake-openrouter-key"

CLUSTERS = [
    {"index": 0, "channels": ["rajasthanroyals", "cricinfo", "aakash chopra"],
     "watches": 500, "share": 0.4},
    {"index": 1, "channels": ["pritam - topic", "arijit singh - topic"],
     "watches": 300, "share": 0.25},
]

FACTS = {
    "rajasthanroyals": {"title": "Rajasthan Royals", "topics": ["Cricket"],
                        "subscribers": 100},
}


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


def reply(text):
    return FakeResponse({"choices": [{"message": {"content": text}}]})


def test_channel_label_joins_the_top_three():
    assert channel_label(["a", "b", "c", "d"]) == "a · b · c"


def test_channel_label_handles_short_clusters():
    assert channel_label(["only"]) == "only"
    assert channel_label([]) == ""


def test_no_call_is_made_without_consent():
    """Consent gates the request itself, not merely whether we use the answer."""
    session = FakeSession(reply('{"0": "Cricket"}'))

    result = name_clusters(CLUSTERS, FACTS, KEY, consented=False, session=session)

    assert result == {}
    assert session.calls == []


def test_no_call_is_made_without_an_api_key():
    session = FakeSession(reply('{"0": "Cricket"}'))

    assert name_clusters(CLUSTERS, FACTS, None, consented=True, session=session) == {}
    assert session.calls == []


def test_names_are_returned_per_cluster_index():
    session = FakeSession(reply('{"0": "IPL Cricket", "1": "Bollywood Playback"}'))

    result = name_clusters(CLUSTERS, FACTS, KEY, consented=True, session=session)

    assert result == {0: "IPL Cricket", 1: "Bollywood Playback"}


def test_only_channel_names_and_topics_are_sent():
    """The privacy contract: no history, no timestamps, no titles, no identity."""
    session = FakeSession(reply('{"0": "Cricket"}'))

    name_clusters(CLUSTERS, FACTS, KEY, consented=True, session=session)

    body = json.dumps(session.calls[0]["json"])
    assert "rajasthanroyals" in body
    assert "Cricket" in body
    for forbidden in ("timestamp", "watches", "share", "video"):
        assert forbidden not in body.lower(), f"{forbidden} must not be sent"


def test_at_most_five_channels_per_cluster_are_sent():
    big = [{"index": 0, "channels": [f"c{i}" for i in range(30)],
            "watches": 1, "share": 1.0}]
    session = FakeSession(reply('{"0": "Something"}'))

    name_clusters(big, {}, KEY, consented=True, session=session)

    body = json.dumps(session.calls[0]["json"])
    assert MAX_CHANNELS_SENT == 5
    assert "c5" not in body


def test_the_configured_model_is_used():
    session = FakeSession(reply('{"0": "Cricket"}'))

    name_clusters(CLUSTERS, FACTS, KEY, consented=True, session=session)

    assert session.calls[0]["json"]["model"] == DEFAULT_MODEL


def test_a_malformed_reply_falls_back_to_no_names():
    session = FakeSession(reply("this is not json"))

    assert name_clusters(CLUSTERS, FACTS, KEY, consented=True, session=session) == {}


def test_an_http_error_falls_back_to_no_names():
    session = FakeSession(FakeResponse({"error": "rate limited"}, status=429))

    assert name_clusters(CLUSTERS, FACTS, KEY, consented=True, session=session) == {}


def test_a_network_error_falls_back_to_no_names():
    class Exploding:
        def post(self, *args, **kwargs):
            raise ConnectionError("down")

    assert name_clusters(CLUSTERS, FACTS, KEY, True, session=Exploding()) == {}


def test_names_are_trimmed_and_bounded():
    session = FakeSession(
        reply('{"0": "   A Very Long Name That Goes On And On Forever   "}')
    )

    result = name_clusters(CLUSTERS, FACTS, KEY, consented=True, session=session)

    assert result[0] == result[0].strip()
    assert len(result[0]) <= 40


def test_json_wrapped_in_prose_is_still_parsed():
    """Free models often wrap JSON in chatter or code fences."""
    session = FakeSession(reply('Sure! ```json\n{"0": "Cricket"}\n```'))

    assert name_clusters(CLUSTERS, FACTS, KEY, consented=True, session=session) == {
        0: "Cricket"
    }


def test_names_for_unknown_cluster_indexes_are_ignored():
    session = FakeSession(reply('{"0": "Cricket", "99": "Nonsense"}'))

    result = name_clusters(CLUSTERS, FACTS, KEY, consented=True, session=session)

    assert result == {0: "Cricket"}
