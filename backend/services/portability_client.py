"""
The only module that talks to Google.

Everything Google-facing lives behind this seam so the rest of the flow can be tested
without credentials or network, and so there is exactly one place to correct when the
API shape changes.

IMPORTANT -- unverified against the live API. The endpoints, resource keys and response
field names below are transcribed from the Data Portability documentation and have never
been exercised against Google. Treat the constants at the top of this file as the things
to check first when the flow does not work end to end.

The backend never stores an access token. Tokens arrive per request from the browser,
are used for a single call, and are not logged or persisted -- which is what keeps the
"we store nothing" promise true while using OAuth.
"""

import csv
import io
from typing import Dict, List, Optional

import requests

# --- Google contract: verify these first if the flow misbehaves ------------------
ARCHIVE_API = "https://dataportability.googleapis.com/v1"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

ARCHIVE_RESOURCES = ["myactivity.youtube"]

USERINFO_API = "https://www.googleapis.com/oauth2/v3/userinfo"

# Google rejects a single OAuth request that mixes data-portability scopes with any
# other scope ("Requests for data portability scopes cannot have non data portability
# scopes"), so the flow needs TWO separate token requests. Each grant produces its own
# access token, and the backend is told which token to use for which call:
#
#   PORTABILITY_SCOPES  -> archive initiate/poll/download
#   OAUTH_SCOPES        -> subscriptions (youtube.readonly) and identity (openid)
PORTABILITY_SCOPES = [
    "https://www.googleapis.com/auth/dataportability.myactivity.youtube",
]

OAUTH_SCOPES = [
    # openid is what lets us verify who the token belongs to. Not a sensitive scope, so
    # it does not widen the OAuth review, and without it we would have to trust a user
    # id sent by the browser -- which would let anyone read anyone's stored Wrapped.
    "openid",
    "https://www.googleapis.com/auth/youtube.readonly",
]

JOB_ID_FIELD = "archiveJobId"
STATE_FIELD = "state"
URLS_FIELD = "urls"
COMPLETE_STATE = "COMPLETE"
FAILED_STATES = {"FAILED", "CANCELLED", "STATE_FAILED"}
# ---------------------------------------------------------------------------------

TIMEOUT = 30
DOWNLOAD_TIMEOUT = 300
DOWNLOAD_CHUNK = 1 << 20  # 1 MiB


class PortabilityError(Exception):
    """Any failure talking to Google, normalised so routes can map it to one status."""


def _headers(access_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _session(session):
    return session if session is not None else requests


def _payload(response) -> Dict:
    try:
        return response.json() or {}
    except ValueError:
        return {}


def _check(response, action: str) -> Dict:
    body = _payload(response)
    if response.status_code >= 400:
        detail = body.get("error", {})
        message = detail.get("message") if isinstance(detail, dict) else str(detail)
        raise PortabilityError(
            f"{action} failed ({response.status_code}): {message or 'no detail'}"
        )
    return body


def initiate_archive(
    access_token: str, session=None, resources: Optional[List[str]] = None
) -> str:
    """Start an export job. Returns the job id."""
    response = _session(session).post(
        f"{ARCHIVE_API}/portabilityArchive:initiate",
        headers=_headers(access_token),
        json={"resources": resources or ARCHIVE_RESOURCES},
        timeout=TIMEOUT,
    )
    body = _check(response, "Starting the export")

    job_id = body.get(JOB_ID_FIELD)
    if not job_id:
        raise PortabilityError(
            f"Google did not return a job id (expected '{JOB_ID_FIELD}'); got: "
            f"{sorted(body)}"
        )
    return job_id


def archive_state(access_token: str, job_id: str, session=None) -> Dict:
    """Check an export job. Returns state, whether it is complete, and any URLs.

    The signed URLs Google returns are short-lived (documented as ~6 hours), which is
    another reason not to persist them anywhere.
    """
    response = _session(session).get(
        f"{ARCHIVE_API}/archiveJobs/{job_id}/portabilityArchiveState",
        headers=_headers(access_token),
        timeout=TIMEOUT,
    )
    body = _check(response, "Checking the export")

    state = body.get(STATE_FIELD, "UNKNOWN")
    if state in FAILED_STATES:
        raise PortabilityError(f"Google reported the export as {state}")

    urls = body.get(URLS_FIELD) or []
    return {"state": state, "complete": state == COMPLETE_STATE, "urls": urls}


def download_archive(urls: List[str], destination: str, session=None) -> str:
    """Stream the archive to a file.

    Streamed to disk rather than held in memory: a real export can run to hundreds of
    megabytes, and ingest_zip reads from a file handle anyway.
    """
    if not urls:
        raise PortabilityError("Google returned no download URLs for the export")

    with open(destination, "wb") as handle:
        for url in urls:
            response = _session(session).get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
            if response.status_code >= 400:
                raise PortabilityError(
                    f"Downloading the export failed ({response.status_code})"
                )
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK):
                if chunk:
                    handle.write(chunk)

    return destination


def fetch_subscriptions(access_token: str, session=None) -> List[Dict]:
    """Every subscription on the account.

    Subscriptions are not part of the portability archive, so they come from the
    YouTube Data API instead. Paginated at 50 per page.
    """
    subscriptions: List[Dict] = []
    page_token = None

    while True:
        params = {"part": "snippet", "mine": "true", "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token

        response = _session(session).get(
            f"{YOUTUBE_API}/subscriptions",
            headers=_headers(access_token),
            params=params,
            timeout=TIMEOUT,
        )
        body = _check(response, "Reading subscriptions")

        for item in body.get("items", []):
            snippet = item.get("snippet", {})
            channel_id = (snippet.get("resourceId") or {}).get("channelId", "")
            subscriptions.append({
                "id": channel_id,
                "title": snippet.get("title", ""),
                "url": f"https://www.youtube.com/channel/{channel_id}" if channel_id else "",
            })

        page_token = body.get("nextPageToken")
        if not page_token:
            return subscriptions


def subscriptions_to_csv(subscriptions: List[Dict]) -> str:
    """Render subscriptions as Takeout's subscriptions.csv.

    Converting to Takeout's shape means preprocess_subscriptions runs unchanged, so the
    OAuth path and the ZIP-upload path produce identical events -- the same reasoning
    behind the HTML connector emitting Takeout JSON.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["Channel Id", "Channel Url", "Channel Title"])
    for item in subscriptions:
        writer.writerow([item.get("id", ""), item.get("url", ""), item.get("title", "")])
    return buffer.getvalue()


def verify_identity(access_token: str, session=None) -> str:
    """Resolve an access token to a Google account id, by asking Google.

    This is the only trustworthy source of a user id. Accepting one sent by the browser
    would let any caller read or delete any other user's stored Wrapped simply by
    claiming their subject.
    """
    response = _session(session).get(
        USERINFO_API, headers=_headers(access_token), timeout=TIMEOUT
    )
    body = _check(response, "Verifying your Google account")

    subject = body.get("sub")
    if not subject:
        raise PortabilityError("Google did not return an account id for this token")
    return subject
