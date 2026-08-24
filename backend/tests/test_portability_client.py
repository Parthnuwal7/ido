"""Tests for portability_client: the only module that talks to Google.

Everything Google-facing is isolated here behind an injectable session, so the rest of
the flow is testable without credentials or network. The request shapes asserted below
come from the Data Portability documentation and have NOT been exercised against the
live API -- these tests pin our side of the contract, not Google's.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.portability_client import (  # noqa: E402
    ARCHIVE_RESOURCES,
    verify_identity,
    PortabilityError,
    archive_state,
    fetch_subscriptions,
    initiate_archive,
    subscriptions_to_csv,
)

TOKEN = "ya29.fake-access-token"


class FakeResponse:
    def __init__(self, payload=None, status=200, chunks=None):
        self._payload = payload or {}
        self.status_code = status
        self._chunks = chunks or []

    def json(self):
        return self._payload

    @property
    def text(self):
        return json.dumps(self._payload)

    def iter_content(self, chunk_size=8192):
        return iter(self._chunks)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeSession:
    """Records calls and replays queued responses."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def _next(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self.responses:
            raise AssertionError(f"unexpected {method} {url}")
        return self.responses.pop(0)

    def post(self, url, **kwargs):
        return self._next("POST", url, **kwargs)

    def get(self, url, **kwargs):
        return self._next("GET", url, **kwargs)


def test_initiate_returns_the_job_id():
    session = FakeSession([FakeResponse({"archiveJobId": "job-123"})])

    assert initiate_archive(TOKEN, session=session) == "job-123"


def test_initiate_sends_the_bearer_token_and_resources():
    session = FakeSession([FakeResponse({"archiveJobId": "job-123"})])

    initiate_archive(TOKEN, session=session)

    call = session.calls[0]
    assert call["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert call["json"]["resources"] == ARCHIVE_RESOURCES


def test_initiate_without_a_job_id_is_an_error():
    session = FakeSession([FakeResponse({"unexpected": "shape"})])

    with pytest.raises(PortabilityError):
        initiate_archive(TOKEN, session=session)


def test_initiate_surfaces_an_http_failure():
    session = FakeSession([FakeResponse({"error": {"message": "denied"}}, status=403)])

    with pytest.raises(PortabilityError) as excinfo:
        initiate_archive(TOKEN, session=session)

    assert "denied" in str(excinfo.value)


def test_state_reports_in_progress_without_urls():
    session = FakeSession([FakeResponse({"state": "IN_PROGRESS"})])

    result = archive_state(TOKEN, "job-123", session=session)

    assert result["state"] == "IN_PROGRESS"
    assert result["urls"] == []
    assert result["complete"] is False


def test_state_reports_complete_with_signed_urls():
    session = FakeSession([
        FakeResponse({"state": "COMPLETE", "urls": ["https://storage/a", "https://storage/b"]})
    ])

    result = archive_state(TOKEN, "job-123", session=session)

    assert result["complete"] is True
    assert result["urls"] == ["https://storage/a", "https://storage/b"]


def test_state_treats_a_failed_job_as_an_error():
    session = FakeSession([FakeResponse({"state": "FAILED"})])

    with pytest.raises(PortabilityError):
        archive_state(TOKEN, "job-123", session=session)


def test_fetch_subscriptions_follows_pagination():
    page_one = {
        "items": [
            {"snippet": {"title": "Chan A",
                         "resourceId": {"channelId": "UC_a"}}},
        ],
        "nextPageToken": "page2",
    }
    page_two = {
        "items": [
            {"snippet": {"title": "Chan B",
                         "resourceId": {"channelId": "UC_b"}}},
        ]
    }
    session = FakeSession([FakeResponse(page_one), FakeResponse(page_two)])

    subs = fetch_subscriptions(TOKEN, session=session)

    assert [s["title"] for s in subs] == ["Chan A", "Chan B"]
    assert session.calls[1]["params"]["pageToken"] == "page2"


def test_fetch_subscriptions_handles_an_empty_account():
    session = FakeSession([FakeResponse({"items": []})])

    assert fetch_subscriptions(TOKEN, session=session) == []


def test_subscriptions_convert_to_the_takeout_csv_shape():
    """Reusing preprocess_subscriptions means matching Takeout's columns exactly."""
    csv_text = subscriptions_to_csv([
        {"id": "UC_a", "title": "Chan A", "url": "https://www.youtube.com/channel/UC_a"},
    ])

    assert csv_text.splitlines()[0] == "Channel Id,Channel Url,Channel Title"
    assert "UC_a" in csv_text and "Chan A" in csv_text


def test_converted_subscriptions_feed_the_existing_preprocessor():
    from services.preprocess_service import preprocess_subscriptions

    csv_text = subscriptions_to_csv([
        {"id": "UC_a", "title": "Chan A", "url": "https://www.youtube.com/channel/UC_a"},
    ])

    (event,) = preprocess_subscriptions(csv_text, "UTC")

    assert event["type"] == "subscribe"
    assert event["channel"] == "Chan A"


# --- identity --------------------------------------------------------------------

def test_verify_identity_returns_the_google_subject():
    """The user id must come from Google, never from whatever the browser claims."""
    session = FakeSession([FakeResponse({"sub": "google-sub-123", "email": "a@b.c"})])

    assert verify_identity(TOKEN, session=session) == "google-sub-123"


def test_verify_identity_sends_the_bearer_token():
    session = FakeSession([FakeResponse({"sub": "google-sub-123"})])

    verify_identity(TOKEN, session=session)

    assert session.calls[0]["headers"]["Authorization"] == f"Bearer {TOKEN}"


def test_verify_identity_rejects_a_response_without_a_subject():
    session = FakeSession([FakeResponse({"email": "a@b.c"})])

    with pytest.raises(PortabilityError):
        verify_identity(TOKEN, session=session)


def test_verify_identity_rejects_an_invalid_token():
    session = FakeSession([FakeResponse({"error": {"message": "invalid"}}, status=401)])

    with pytest.raises(PortabilityError):
        verify_identity(TOKEN, session=session)
