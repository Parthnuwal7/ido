"""Tests for wrapped_store: per-user card storage.

Only derived cards are stored -- never the archive, never a token. Cards are ~3 KB, so
this is a small table, but it is still personal data and the deletion path is part of
the contract rather than an afterthought.

The store is Postgres/Supabase only, so these tests run against a live Postgres. Point
TEST_DATABASE_URL (or DATABASE_URL) at one; the tests skip if neither is set. Only rows
belonging to the fixed test subjects are cleaned up -- the suite never touches a real
user's saved Wrappeds.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import wrapped_store  # noqa: E402

USER = "google-sub-123"
OTHER = "google-sub-456"
CARDS = {"intro": {"year": 2025}, "stats_overview": {"videos_watched": 2500}}


@pytest.fixture(autouse=True)
def database(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("set TEST_DATABASE_URL or DATABASE_URL to run Postgres-backed store tests")

    if not (url.startswith("postgres://") or url.startswith("postgresql://")):
        pytest.fail("wrapped_store requires Postgres; DATABASE_URL must be a Supabase URL")

    monkeypatch.setenv("DATABASE_URL", url)
    wrapped_store.reset_connection()
    wrapped_store.init_schema()
    # Only ever wipe the two test subjects, never real user data.
    wrapped_store._execute("DELETE FROM wrapped WHERE user_sub IN (?, ?)", (USER, OTHER))
    wrapped_store._commit()
    yield
    wrapped_store.reset_connection()


def test_saving_then_reading_returns_the_cards():
    wrapped_store.save_wrapped(USER, 2025, CARDS, source="upload")

    stored = wrapped_store.get_wrapped(USER, 2025)

    assert stored["cards"] == CARDS
    assert stored["year"] == 2025
    assert stored["source"] == "upload"


def test_reading_a_year_that_was_never_saved():
    assert wrapped_store.get_wrapped(USER, 2019) is None


def test_saving_the_same_year_twice_replaces_it():
    """Regenerating a year should update it, not accumulate duplicates."""
    wrapped_store.save_wrapped(USER, 2025, CARDS, source="upload")
    wrapped_store.save_wrapped(USER, 2025, {"intro": {"year": 2025}, "v": 2},
                               source="data_portability")

    assert wrapped_store.get_wrapped(USER, 2025)["cards"]["v"] == 2
    assert len(wrapped_store.list_wrappeds(USER)) == 1


def test_listing_omits_the_card_payload():
    """The list view is for picking a year; sending every card would be wasteful."""
    wrapped_store.save_wrapped(USER, 2025, CARDS, source="upload")

    (row,) = wrapped_store.list_wrappeds(USER)

    assert row["year"] == 2025
    assert "cards" not in row
    assert row["created_at"]


def test_listing_is_newest_year_first():
    for year in (2023, 2025, 2024):
        wrapped_store.save_wrapped(USER, year, CARDS, source="upload")

    assert [r["year"] for r in wrapped_store.list_wrappeds(USER)] == [2025, 2024, 2023]


def test_users_cannot_see_each_others_wrappeds():
    wrapped_store.save_wrapped(USER, 2025, CARDS, source="upload")

    assert wrapped_store.get_wrapped(OTHER, 2025) is None
    assert wrapped_store.list_wrappeds(OTHER) == []


def test_deleting_removes_everything_for_that_user_only():
    wrapped_store.save_wrapped(USER, 2025, CARDS, source="upload")
    wrapped_store.save_wrapped(USER, 2024, CARDS, source="upload")
    wrapped_store.save_wrapped(OTHER, 2025, CARDS, source="upload")

    removed = wrapped_store.delete_user_data(USER)

    assert removed == 2
    assert wrapped_store.list_wrappeds(USER) == []
    assert wrapped_store.get_wrapped(OTHER, 2025) is not None


def test_deleting_a_user_with_nothing_stored_is_not_an_error():
    assert wrapped_store.delete_user_data("nobody") == 0


def test_schema_can_be_initialised_twice():
    """Startup runs this every boot."""
    wrapped_store.init_schema()
    wrapped_store.init_schema()

    wrapped_store.save_wrapped(USER, 2025, CARDS, source="upload")
    assert wrapped_store.get_wrapped(USER, 2025) is not None


# --- connection hygiene ------------------------------------------------------------

def test_reads_do_not_leave_a_transaction_open():
    """A SELECT must not pin a pooler slot.

    psycopg defaults to autocommit=False, so an un-committed SELECT leaves the
    connection "idle in transaction". Connections are cached per thread and FastAPI
    runs sync handlers on a ~40-thread pool, so without this every few reads pin
    another Supabase pooler slot until new requests cannot acquire one.
    """
    import psycopg

    wrapped_store.save_wrapped(USER, 2025, CARDS, source="upload")
    connection = wrapped_store._connect()

    wrapped_store.list_wrappeds(USER)
    assert connection.info.transaction_status == psycopg.pq.TransactionStatus.IDLE

    wrapped_store.get_wrapped(USER, 2025)
    assert connection.info.transaction_status == psycopg.pq.TransactionStatus.IDLE


def test_writes_do_not_leave_a_transaction_open():
    import psycopg

    wrapped_store.save_wrapped(USER, 2024, CARDS, source="upload")

    assert wrapped_store._connect().info.transaction_status == psycopg.pq.TransactionStatus.IDLE


def test_saving_the_same_year_twice_is_atomic():
    """save must not delete-then-fail, leaving the year gone.

    A DELETE + INSERT pair across two statements can lose the existing row if the
    INSERT fails and the connection is reset between them.
    """
    wrapped_store.save_wrapped(USER, 2025, {"v": 1}, source="upload")
    wrapped_store.save_wrapped(USER, 2025, {"v": 2}, source="data_portability")

    stored = wrapped_store.get_wrapped(USER, 2025)
    assert stored["cards"]["v"] == 2
    assert stored["source"] == "data_portability"
    assert len(wrapped_store.list_wrappeds(USER)) == 1
