"""Handlers that do blocking work must be sync `def`, not `async def`.

FastAPI runs a sync `def` handler in a threadpool but runs an `async def` handler on the
event loop itself. `ingest_zip` does a multi-second regex scan plus enrichment over tens
of thousands of events, and `generate_wrapped_cards` is pure CPU. Declared `async`, one
upload freezes every other request to the process for its whole duration.

This is a structural assertion rather than a timing one: a concurrency race would be
flaky, while "is this a coroutine function" is exactly the property that decides which
executor FastAPI uses.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import portability_routes, wrapped_routes  # noqa: E402

BLOCKING_HANDLERS = [
    (wrapped_routes, "generate_wrapped"),
    (wrapped_routes, "generate_demo"),
    (portability_routes, "initiate"),
    (portability_routes, "status"),
    (portability_routes, "generate"),
]


def test_blocking_handlers_are_not_declared_async():
    offenders = [
        f"{module.__name__}.{name}"
        for module, name in BLOCKING_HANDLERS
        if inspect.iscoroutinefunction(getattr(module, name))
    ]

    assert not offenders, (
        "these run blocking work on the event loop; declare them `def` so FastAPI "
        f"threadpools them: {offenders}"
    )
