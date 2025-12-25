"""
Session management API routes
Endpoints for storing and retrieving session data
"""

from fastapi import APIRouter, HTTPException
from models.schemas import SessionStoreRequest, SessionResponse, SessionData
from services.session_service import (
    create_session,
    get_session,
    delete_session,
    list_sessions,
    cleanup_expired_sessions
)

router = APIRouter()


@router.post("/store", response_model=SessionResponse)
async def store_session(request: SessionStoreRequest):
    """
    Store extracted files in a session with a unique token.
    
    Returns session token for future retrieval.
    """
    try:
        # Convert Pydantic models to dicts for storage
        files_dict = [f.model_dump() for f in request.files]
        result = create_session(files_dict, request.timezone)
        
        return SessionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing session: {str(e)}")


@router.get("/{token}", response_model=SessionData)
async def get_session_data(token: str):
    """
    Retrieve session data by token.
    """
    session = get_session(token)
    
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionData(**session)


@router.delete("/{token}")
async def delete_session_data(token: str):
    """
    Delete a session by token.
    """
    deleted = delete_session(token)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully", "token": token}


@router.get("/")
async def list_all_sessions():
    """
    List all sessions (for debugging).
    """
    sessions = list_sessions()
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/cleanup")
async def cleanup_sessions(max_age_hours: int = 24):
    """
    Clean up expired sessions.
    
    Args:
        max_age_hours: Maximum age in hours (default: 24)
    """
    deleted_count = cleanup_expired_sessions(max_age_hours)
    return {"deleted_count": deleted_count, "max_age_hours": max_age_hours}
