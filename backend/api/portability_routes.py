"""
Google Data Portability routes.

The browser owns the OAuth tokens. It completes consent and passes the access tokens on
each call; the backend uses them once and drops them. Nothing about the user -- token,
job id, signed URLs, or the archive -- is stored, which is what lets the OAuth flow
coexist with the project's "we store nothing" promise.

Two tokens are involved, because Google forbids mixing data-portability scopes with
other scopes in a single request:
  * portability token -> archive initiate/poll/download (`access_token`)
  * oauth token       -> subscriptions + identity (`oauth_token`, openid + youtube.readonly)

Polling is client-driven for the same reason, plus a practical one: Hugging Face Spaces
sleeps when idle, so a server-side polling loop would die mid-job. Each poll from the
browser wakes the Space instead.

Handlers are sync `def` on purpose. The Google calls use blocking `requests`, and
FastAPI runs sync handlers in a threadpool -- declaring them `async` would block the
event loop for the length of every Google round trip.
"""

import os
import traceback
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services import portability_client, wrapped_store
from services.portability_client import PortabilityError
from services.portability_service import build_wrapped

portability_router = APIRouter(prefix="/api/portability", tags=["Data Portability"])


class TokenRequest(BaseModel):
    access_token: str


class StatusRequest(TokenRequest):
    job_id: str


class GenerateRequest(TokenRequest):
    urls: List[str]
    timezone: str = "UTC"
    year: Optional[int] = None
    # Second token from a separate grant: carries openid + youtube.readonly, used for
    # identity (saving) and subscriptions (not present in the portability archive).
    oauth_token: Optional[str] = None


@portability_router.get("/config")
def portability_config():
    """What the browser needs to start OAuth, without hardcoding it in the frontend.

    Two OAuth clients are required: Google forbids mixing data-portability scopes with
    any other scope, and `include_granted_scopes` means one client can never hold both
    sets. So the portability client and the account client are separate:
      * GOOGLE_CLIENT_ID        -> dataportability.myactivity.youtube (export)
      * GOOGLE_OAUTH_CLIENT_ID  -> openid + youtube.readonly (identity + subscriptions)
    """
    portability_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    oauth_client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    return {
        "configured": bool(portability_client_id and oauth_client_id),
        "client_id": portability_client_id,
        "oauth_client_id": oauth_client_id,
        "portability_scopes": portability_client.PORTABILITY_SCOPES,
        "oauth_scopes": portability_client.OAUTH_SCOPES,
    }


@portability_router.post("/initiate")
def initiate(request: TokenRequest):
    """Start a Google export job. Returns the job id for the browser to poll."""
    try:
        job_id = portability_client.initiate_archive(request.access_token)
    except PortabilityError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not start the export: {exc}")

    print(f"[Portability] Started export job {job_id}")
    return {"job_id": job_id}


@portability_router.post("/status")
def status(request: StatusRequest):
    """Check an export job. The browser calls this on an interval."""
    try:
        result = portability_client.archive_state(request.access_token, request.job_id)
    except PortabilityError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not check the export: {exc}")

    print(f"[Portability] Job {request.job_id} state: {result['state']}")
    return result


@portability_router.post("/generate")
def generate(request: GenerateRequest):
    """Download the finished export and return Wrapped cards.

    The archive is streamed to a temp file, processed, and deleted before responding.
    """
    if not request.urls:
        raise HTTPException(status_code=400, detail="The export returned no download URLs")

    print("[Portability] Downloading and processing the finished export...")
    try:
        cards = build_wrapped(
            request.access_token, request.urls,
            timezone=request.timezone, year=request.year,
            oauth_token=request.oauth_token,
        )
    except PortabilityError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Portability generation failed: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}")

    if "error" in cards:
        raise HTTPException(status_code=400, detail=cards["error"])

    _save_for_user(request.oauth_token, cards)

    print("[Portability] Wrapped generated and returned to the browser")
    return JSONResponse(content=cards)


def _save_for_user(oauth_token: str, cards: dict) -> None:
    """Store the result against the Google account, best effort.

    Identity is resolved with Google rather than taken on trust. It needs the openid
    token, which is the *oauth* grant, not the portability one. A storage failure must
    not cost the user the Wrapped they just waited an hour for, so this never raises --
    they simply do not get to revisit it later.
    """
    try:
        subject = portability_client.verify_identity(oauth_token)
        year = (cards.get("metadata") or {}).get("year")
        if year:
            wrapped_store.save_wrapped(subject, year, cards, source="data_portability")
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Could not save this Wrapped for later: {exc}")
