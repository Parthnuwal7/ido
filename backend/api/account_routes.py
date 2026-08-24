"""
Account routes: a user's stored Wrappeds.

Identity comes from Google, never from the request body. Every handler resolves the
bearer token to a Google account id by asking Google, so a caller cannot read or delete
another user's data by claiming their subject.

Only generated cards are stored. The uploaded archive and the access token are not.

Handlers are sync `def` so FastAPI runs the blocking Google and database calls in a
threadpool rather than on the event loop.
"""

import traceback

from fastapi import APIRouter, Depends, Header, HTTPException

from services import portability_client, wrapped_store
from services.portability_client import PortabilityError

account_router = APIRouter(prefix="/api/me", tags=["Account"])


def current_user(authorization: str = Header(default="")) -> str:
    """Resolve `Authorization: Bearer <google access token>` to a Google account id."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in with Google to continue")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in with Google to continue")

    try:
        return portability_client.verify_identity(token)
    except PortabilityError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not verify your account: {exc}")


@account_router.get("/wrapped")
def list_wrapped(user: str = Depends(current_user)):
    """Years this user has stored, newest first. Card payloads are omitted."""
    return {"wrappeds": wrapped_store.list_wrappeds(user)}


@account_router.get("/wrapped/{year}")
def get_wrapped(year: int, user: str = Depends(current_user)):
    """One stored year's cards."""
    stored = wrapped_store.get_wrapped(user, year)
    if stored is None:
        raise HTTPException(status_code=404, detail=f"No saved Wrapped for {year}")
    return stored


@account_router.delete("/data")
def delete_data(user: str = Depends(current_user)):
    """Delete everything stored for this user.

    Part of the interface rather than an afterthought: storing derived personal data
    obliges us to be able to remove it on request.
    """
    return {"deleted": wrapped_store.delete_user_data(user)}
