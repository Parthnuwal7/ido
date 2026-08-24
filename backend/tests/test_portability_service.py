"""Tests for portability_service: archive -> Wrapped cards.

Google is faked at the client seam, so this exercises the real download-to-disk,
ingest_zip, subscription merge and card generation without credentials.
"""
import io
import os
import shutil
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.portability_client import PortabilityError  # noqa: E402
from services.portability_service import build_wrapped  # noqa: E402

DEMO_ZIP = os.path.join(os.path.dirname(__file__), "..", "fixtures", "demo_takeout.zip")
BASE = "Takeout/YouTube and YouTube Music"
NBSP, NNBSP = "\xa0", " "


def history_only_zip(path):
    """A Takeout archive with watch history but no subscriptions.csv."""
    cell = (
        '<div class="outer-cell mdl-cell"><div class="mdl-grid">'
        '<div class="header-cell mdl-cell mdl-cell--12-col">'
        '<p class="mdl-typography--title">YouTube<br></p></div>'
        '<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">'
        f'Watched{NBSP}<a href="https://www.youtube.com/watch?v=a">A Video</a><br>'
        '<a href="https://www.youtube.com/channel/UCx">Chan</a><br>'
        f'Aug 21, 2025, 12:13:55{NNBSP}PM UTC<br></div>'
        '<div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">'
        "<b>Products:</b><br>&emsp;YouTube</div></div></div>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{BASE}/history/watch-history.html", cell * 20)
    return path


class FakeClient:
    """Stands in for portability_client."""

    def __init__(self, source_zip, subscriptions=None):
        self.source_zip = source_zip
        self.subscriptions = subscriptions or []
        self.downloaded_to = None
        self.fetched_subscriptions = False

    def download_archive(self, urls, destination, session=None):
        shutil.copyfile(self.source_zip, destination)
        self.downloaded_to = destination
        return destination

    def fetch_subscriptions(self, access_token, session=None):
        self.fetched_subscriptions = True
        return self.subscriptions

    def subscriptions_to_csv(self, subscriptions):
        from services.portability_client import subscriptions_to_csv
        return subscriptions_to_csv(subscriptions)


def test_builds_cards_from_the_downloaded_archive():
    client = FakeClient(DEMO_ZIP)

    cards = build_wrapped("tok", ["https://signed/url"], year=2025, client=client)

    assert "error" not in cards
    assert cards["stats_overview"]["videos_watched"] == 2500
    assert cards["personality"]["type"] == "Night Owl"


def test_the_archive_is_actually_downloaded():
    client = FakeClient(DEMO_ZIP)

    build_wrapped("tok", ["https://signed/url"], year=2025, client=client)

    assert client.downloaded_to is not None


def test_subscriptions_are_fetched_when_the_archive_has_none(tmp_path):
    """The portability archive does not include subscriptions; the Data API does."""
    client = FakeClient(
        history_only_zip(str(tmp_path / "a.zip")),
        subscriptions=[
            {"id": "UC_a", "title": "Chan A", "url": "https://www.youtube.com/channel/UC_a"},
            {"id": "UC_b", "title": "Chan B", "url": "https://www.youtube.com/channel/UC_b"},
        ],
    )

    cards = build_wrapped("tok", ["https://signed/url"], year=2025, oauth_token="tok", client=client)

    assert client.fetched_subscriptions is True
    assert cards["subscriptions"]["total"] == 2


def test_subscriptions_in_the_archive_are_not_refetched():
    """The demo archive already carries subscriptions.csv."""
    client = FakeClient(DEMO_ZIP)

    build_wrapped("tok", ["https://signed/url"], year=2025, oauth_token="tok", client=client)

    assert client.fetched_subscriptions is False


def test_temporary_archive_is_removed():
    client = FakeClient(DEMO_ZIP)

    build_wrapped("tok", ["https://signed/url"], year=2025, client=client)

    assert not os.path.exists(client.downloaded_to)


def test_temporary_archive_is_removed_even_on_failure(tmp_path):
    """A user's export must not be left on disk when processing blows up."""
    class Exploding(FakeClient):
        def download_archive(self, urls, destination, session=None):
            super().download_archive(urls, destination, session)
            raise PortabilityError("network died mid-download")

    client = Exploding(DEMO_ZIP)

    with pytest.raises(PortabilityError):
        build_wrapped("tok", ["https://signed/url"], year=2025, client=client)

    assert not os.path.exists(client.downloaded_to)


def test_a_subscription_fetch_failure_does_not_lose_the_wrapped(tmp_path):
    """Subscriptions are one card; losing them should not cost the other eighteen."""
    class NoSubs(FakeClient):
        def fetch_subscriptions(self, access_token, session=None):
            raise PortabilityError("insufficient scope")

    client = NoSubs(history_only_zip(str(tmp_path / "b.zip")))

    cards = build_wrapped("tok", ["https://signed/url"], year=2025, oauth_token="tok", client=client)

    assert "error" not in cards
    assert cards["subscriptions"]["total"] == 0


def test_missing_oauth_token_skips_subscriptions_gracefully(tmp_path):
    """No oauth grant (e.g. only the portability popup consented) must not break the run."""
    client = FakeClient(
        history_only_zip(str(tmp_path / "c.zip")),
        subscriptions=[{"id": "UC_a", "title": "Chan A", "url": "https://x"}],
    )

    cards = build_wrapped("tok", ["https://signed/url"], year=2025, client=client)

    assert client.fetched_subscriptions is False
    assert "error" not in cards
    assert cards["subscriptions"]["total"] == 0
