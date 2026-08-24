"""
Per-user storage of generated Wrapped cards.

Stores only what the pipeline produced -- never the uploaded archive, never an OAuth
token. Cards serialise to roughly 3 KB, so a user's entire history here is smaller than
their avatar.

This is still personal data ("your most-watched channel is X, you watch 40% after
midnight"), so delete_user_data() is part of the interface rather than something bolted
on later.

The backend is Supabase (Postgres) only. DATABASE_URL is required -- there is no
local-file fallback, so development and production behave identically:

    postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres

Use the **Transaction pooler** URI (port 6543) for containers/serverless; the code
disables server-side prepared statements so pgbouncer is happy.
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

_local = threading.local()


class StorageError(Exception):
    """Raised when the database is not configured. Kept thin so routes can map it."""


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise StorageError(
            "DATABASE_URL is not set. Point it at your Supabase connection string "
            "(see backend/env.example) -- the store no longer falls back to SQLite."
        )
    if not (url.startswith("postgres://") or url.startswith("postgresql://")):
        raise StorageError(
            "DATABASE_URL must be a postgres:// or postgresql:// Supabase URL; "
            f"got: {url[:30]}..."
        )
    return url


def _connect():
    """One connection per thread. FastAPI runs sync handlers in a threadpool."""
    connection = getattr(_local, "connection", None)
    if connection is not None:
        return connection

    import psycopg  # imported lazily so a missing driver fails loudly at first use

    # autocommit=True is required, not cosmetic: psycopg defaults to False, which leaves
    # every SELECT sitting in an open transaction. Connections are cached per thread and
    # FastAPI runs sync handlers on a large threadpool, so without this each read pins
    # another Supabase pooler slot as "idle in transaction" until the pool is exhausted.
    #
    # prepare_threshold=None disables server-side prepared statements. Supabase's
    # transaction pooler (port 6543) runs pgbouncer, which cannot support them and
    # fails with "prepared statement already exists" once psycopg starts using them.
    connection = psycopg.connect(
        _database_url(), autocommit=True, prepare_threshold=None
    )

    _local.connection = connection
    return connection


def reset_connection() -> None:
    """Drop the cached connection. Used by tests switching databases."""
    connection = getattr(_local, "connection", None)
    if connection is not None:
        try:
            connection.close()
        except Exception:
            pass
    _local.connection = None


def _sql(statement: str) -> str:
    """Written with ? placeholders, translated to %s for Postgres."""
    return statement.replace("?", "%s")


def _execute(statement: str, params=()):
    """Run a statement, reconnecting once if the pooled connection has gone stale.

    Supabase drops idle connections, and this backend can sit idle for a long
    time between visitors. Without the retry, the first request after a quiet period
    fails with a broken-connection error.
    """
    try:
        cursor = _connect().cursor()
        cursor.execute(_sql(statement), params)
        return cursor
    except Exception:
        reset_connection()
        cursor = _connect().cursor()
        cursor.execute(_sql(statement), params)
        return cursor


def _commit() -> None:
    connection = _connect()
    if hasattr(connection, "commit"):
        connection.commit()


def init_schema() -> None:
    """Create the table if it is missing. Safe to run on every boot."""
    _execute(
        """
        CREATE TABLE IF NOT EXISTS wrapped (
            user_sub   TEXT NOT NULL,
            year       INTEGER NOT NULL,
            source     TEXT,
            cards      TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_sub, year)
        )
        """
    )
    _commit()


def save_wrapped(user_sub: str, year: int, cards: Dict, source: str = "upload") -> Dict:
    """Store (or replace) one year's cards for a user."""
    created_at = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(cards, ensure_ascii=False, default=str)

    # One statement, not DELETE + INSERT: that pair can lose the existing row if the
    # INSERT fails between them, which _execute's reconnect-retry makes reachable.
    _execute(
        "INSERT INTO wrapped (user_sub, year, source, cards, created_at) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (user_sub, year) DO UPDATE SET "
        "source = EXCLUDED.source, cards = EXCLUDED.cards, "
        "created_at = EXCLUDED.created_at",
        (user_sub, year, source, payload, created_at),
    )
    _commit()

    return {"year": year, "source": source, "created_at": created_at}


def get_wrapped(user_sub: str, year: int) -> Optional[Dict]:
    """One year's stored cards, or None."""
    row = _execute(
        "SELECT year, source, cards, created_at FROM wrapped "
        "WHERE user_sub = %s AND year = %s",
        (user_sub, year),
    ).fetchone()

    if row is None:
        return None

    return {
        "year": row[0],
        "source": row[1],
        "cards": json.loads(row[2]),
        "created_at": row[3],
    }


def list_wrappeds(user_sub: str) -> List[Dict]:
    """Years this user has stored, newest first, without the card payloads."""
    rows = _execute(
        "SELECT year, source, created_at FROM wrapped WHERE user_sub = %s "
        "ORDER BY year DESC",
        (user_sub,),
    ).fetchall()

    return [{"year": r[0], "source": r[1], "created_at": r[2]} for r in rows]


def delete_user_data(user_sub: str) -> int:
    """Remove everything stored for a user. Returns how many rows went."""
    cursor = _execute("DELETE FROM wrapped WHERE user_sub = %s", (user_sub,))
    _commit()
    return cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
