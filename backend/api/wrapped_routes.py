"""
Wrapped API Routes
Stateless endpoint for generating YouTube Wrapped cards.

Ingest lives in services.takeout_ingest so it can be tested without FastAPI; this module
is only HTTP concerns. Note that no HTTPException is raised inside a try block here --
HTTPException subclasses Exception, so a broad `except Exception` would swallow an
intended 4xx and re-raise it as a 500.

Handlers here are sync `def` on purpose. ingest_zip and generate_wrapped_cards are
blocking CPU work measured in seconds; FastAPI runs sync handlers in a threadpool but
runs `async def` handlers on the event loop, where one upload would freeze every other
request to the process. Do not convert these to `async def`.
"""

import traceback
import zipfile
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from services import interest_vectors
from services.demo_service import DEMO_YEAR, demo_archive_bytes, load_demo_cards
from services.takeout_ingest import HistoryParseError, build_enrichment, ingest_zip
from services.wrapped_service import generate_wrapped_cards

wrapped_router = APIRouter(prefix="/api/wrapped", tags=["Wrapped"])

NO_HISTORY_DETAIL = (
    "No YouTube history found in this ZIP. Make sure you selected YouTube in Google "
    "Takeout and that the export includes 'history'."
)


def _no_data_for_year(result) -> str:
    """Name the years that do have data, so the user can pick a usable one."""
    if not result.years_available:
        return NO_HISTORY_DETAIL

    years = ", ".join(str(y) for y in result.years_available)
    return (
        f"No watch history for {result.year} in this export. "
        f"Years with data: {years}."
    )


@wrapped_router.post("/generate")
def generate_wrapped(
    file: UploadFile = File(...),
    timezone: str = Form(default="UTC"),
    year: Optional[int] = Form(default=None),
    name_interests: bool = Form(default=False),
):
    """
    Generate YouTube Wrapped cards from a takeout ZIP file.

    Stateless - no data is stored on the server. Accepts either the JSON or the HTML
    export format; Takeout produces HTML by default.

    Args:
        file: YouTube takeout ZIP file
        timezone: User's timezone (e.g. "Asia/Kolkata", "America/New_York")
        year: Calendar year to cover. Defaults to the current year, falling back to
            the most recent year with watch history.
        name_interests: User consent to send a few channel names to an LLM for nicer
            taste-world names. Off by default; without it the worlds are labelled with
            the user's own channel names.

    Returns:
        JSON with all card data for rendering the wrapped experience.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")

    # UploadFile already spools large bodies to a temp file. Passing the handle rather
    # than `await file.read()` keeps a multi-hundred-MB upload off the heap.
    try:
        result = ingest_zip(file.file, timezone, year=year)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except HistoryParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - surface unexpected failures as 500
        print(f"[ERROR] Takeout ingest failed: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}")

    if not result.events:
        raise HTTPException(status_code=400, detail=NO_HISTORY_DETAIL)

    if result.stats["total_watch"] == 0:
        raise HTTPException(status_code=400, detail=_no_data_for_year(result))

    try:
        watch_events = [e for e in result.events if e.get("type") == "watch"]
        interest = interest_vectors.analyse(watch_events)
        enrichment = build_enrichment(watch_events, interest, name_interests)
        cards = generate_wrapped_cards(result.events, result.stats, enrichment)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Card generation failed: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}")

    if "error" in cards:
        raise HTTPException(status_code=400, detail=cards["error"])

    metadata = cards.setdefault("metadata", {})
    metadata["year"] = result.year
    metadata["years_available"] = result.years_available
    if result.report:
        metadata["parse_report"] = result.report

    return JSONResponse(content=cards)


@wrapped_router.get("/demo")
def generate_demo():
    """Wrapped cards for the seeded demo history.

    Runs the committed fixtures through the same pipeline as a real upload, so the demo
    always reflects what the code actually produces. Cached after the first request.
    """
    try:
        cards = load_demo_cards()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Demo generation failed: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Demo unavailable: {exc}")

    return JSONResponse(content=cards)


@wrapped_router.get("/demo-file")
def demo_file():
    """The seeded Takeout archive, for the browser to submit like a real upload.

    The demo used to call its own endpoint, which skipped everything between the ZIP
    and the cards. Handing the browser the actual file means "Try the demo" exercises
    the same route a user's own export does, and breaks in the same places.

    X-Demo-Year tells the client which year the archive covers, so the year selector
    does not send the current year at an archive that has no history for it.
    """
    try:
        data = demo_archive_bytes()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Demo archive unavailable: {exc}")
        raise HTTPException(status_code=500, detail="Demo file unavailable")

    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="ido-demo-takeout.zip"',
            "X-Demo-Year": str(DEMO_YEAR),
            "Access-Control-Expose-Headers": "X-Demo-Year",
        },
    )
