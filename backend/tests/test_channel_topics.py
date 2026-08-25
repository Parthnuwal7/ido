"""Tests for channel_topics: the YouTube Data API seam.

Google is faked through an injectable session, so these run without a key or network.
The service must never raise into the pipeline -- a missing key or a failed call means
fewer cards, never a failed Wrapped.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.channel_topics import (  # noqa: E402
    BATCH_SIZE,
    channel_id_from_url,
    fetch,
)

KEY = "fake-api-key"


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected extra request")
        return self.responses.pop(0)


def item(channel_id, title, topics=None, subscribers="1000"):
    entry = {
        "id": channel_id,
        "snippet": {"title": title},
        "statistics": {"subscriberCount": subscribers},
    }
    if topics is not None:
        entry["topicDetails"] = {"topicCategories": topics}
    return entry


def test_extracts_a_channel_id_from_a_takeout_url():
    url = "https://www.youtube.com/channel/UCpg-rSVxo3EgwEmWHl2nN9A"

    assert channel_id_from_url(url) == "UCpg-rSVxo3EgwEmWHl2nN9A"


def test_ignores_urls_that_are_not_channel_links():
    assert channel_id_from_url("https://www.youtube.com/watch?v=abc") is None
    assert channel_id_from_url("") is None
    assert channel_id_from_url(None) is None


def test_returns_none_without_an_api_key():
    """No key configured is a normal state, not an error."""
    assert fetch(["UC_a"], None) is None
    assert fetch(["UC_a"], "") is None


def test_maps_ids_to_title_topics_and_subscribers():
    payload = {"items": [item(
        "UC_a", "Chan A",
        topics=["https://en.wikipedia.org/wiki/Cricket"],
        subscribers="1234",
    )]}
    session = FakeSession([FakeResponse(payload)])

    facts = fetch(["UC_a"], KEY, session=session)

    assert facts["UC_a"]["title"] == "Chan A"
    assert facts["UC_a"]["topics"] == ["Cricket"]
    assert facts["UC_a"]["subscribers"] == 1234


def test_topic_urls_are_reduced_to_readable_names():
    payload = {"items": [item(
        "UC_a", "Chan A",
        topics=["https://en.wikipedia.org/wiki/Electronic_music"],
    )]}
    session = FakeSession([FakeResponse(payload)])

    facts = fetch(["UC_a"], KEY, session=session)

    assert facts["UC_a"]["topics"] == ["Electronic music"]


def test_batches_ids_fifty_at_a_time():
    """channels.list accepts 50 ids per request at 1 quota unit."""
    ids = [f"UC_{i}" for i in range(120)]
    session = FakeSession([
        FakeResponse({"items": []}), FakeResponse({"items": []}),
        FakeResponse({"items": []}),
    ])

    fetch(ids, KEY, session=session)

    assert BATCH_SIZE == 50
    assert len(session.calls) == 3
    assert len(session.calls[0]["params"]["id"].split(",")) == 50


def test_channels_without_topics_still_return_facts():
    session = FakeSession([FakeResponse({"items": [item("UC_a", "Chan A")]})])

    facts = fetch(["UC_a"], KEY, session=session)

    assert facts["UC_a"]["topics"] == []


def test_a_failed_request_returns_none_rather_than_raising():
    session = FakeSession([FakeResponse({"error": {"message": "bad key"}}, status=403)])

    assert fetch(["UC_a"], KEY, session=session) is None


def test_a_network_error_returns_none_rather_than_raising():
    class Exploding:
        def get(self, *args, **kwargs):
            raise ConnectionError("network down")

    assert fetch(["UC_a"], KEY, session=Exploding()) is None


def test_an_empty_id_list_makes_no_request():
    session = FakeSession([])

    assert fetch([], KEY, session=session) == {}
    assert session.calls == []


# --- concurrency -------------------------------------------------------------------

def test_batches_are_fetched_concurrently():
    """Six sequential round-trips at ~0.66s each cost 4s; concurrently they cost one.

    Asserted by timing rather than by inspection: a sleeping fake session makes the
    difference unambiguous without depending on how concurrency is implemented.
    """
    import time

    class SlowSession:
        def get(self, url, **kwargs):
            time.sleep(0.2)
            return FakeResponse({"items": []})

    ids = [f"UC_{i}" for i in range(250)]      # 5 batches of 50

    start = time.perf_counter()
    fetch(ids, KEY, session=SlowSession())
    elapsed = time.perf_counter() - start

    assert elapsed < 0.6, (
        f"5 batches took {elapsed:.2f}s; sequential would be ~1.0s, so these ran serially"
    )


def test_results_from_all_batches_are_merged():
    """Concurrency must not drop or duplicate a batch."""
    class PerBatchSession:
        def __init__(self):
            self.seen = 0

        def get(self, url, **kwargs):
            requested = kwargs["params"]["id"].split(",")
            return FakeResponse({
                "items": [item(cid, f"Chan {cid}") for cid in requested]
            })

    ids = [f"UC_{i}" for i in range(120)]

    facts = fetch(ids, KEY, session=PerBatchSession())

    assert len(facts) == 120
    assert facts["UC_0"]["title"] == "Chan UC_0"
    assert facts["UC_119"]["title"] == "Chan UC_119"


def test_one_failing_batch_still_returns_none():
    """A partial result would silently under-report; keep the all-or-nothing contract."""
    class FlakySession:
        def __init__(self):
            self.calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            if self.calls == 2:
                return FakeResponse({"error": {"message": "quota"}}, status=403)
            return FakeResponse({"items": []})

    assert fetch([f"UC_{i}" for i in range(150)], KEY, session=FlakySession()) is None
