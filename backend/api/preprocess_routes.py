"""
Preprocessing API routes
Endpoints for preprocessing YouTube Takeout data into normalized Event format
"""

from fastapi import APIRouter, HTTPException
from models.schemas import (
    PreprocessRequest, 
    PreprocessResult, 
    PreprocessStats,
    LanguageBreakdown,
    Event,
    PreprocessedSessionData
)
from services.preprocess_service import (
    preprocess_watch_history,
    preprocess_search_history,
    preprocess_subscriptions,
    preprocess_all_files
)
from services.session_service import create_session, get_session
from datetime import datetime
import uuid
import json
from pathlib import Path

router = APIRouter()

# Storage for preprocessed sessions
STORAGE_DIR = Path(__file__).parent.parent / "storage"


@router.post("/watch-history", response_model=list[Event])
async def preprocess_watch(request: PreprocessRequest):
    """
    Preprocess watch-history.json only.
    
    Returns list of normalized watch events.
    """
    watch_file = None
    for f in request.files:
        if f.filename == "watch-history.json":
            watch_file = f
            break
    
    if not watch_file:
        raise HTTPException(status_code=400, detail="watch-history.json not found in files")
    
    events = preprocess_watch_history(watch_file.content, request.timezone)
    return [Event(**e) for e in events]


@router.post("/search-history", response_model=list[Event])
async def preprocess_search(request: PreprocessRequest):
    """
    Preprocess search-history.json only.
    
    Returns list of normalized search events.
    """
    search_file = None
    for f in request.files:
        if f.filename == "search-history.json":
            search_file = f
            break
    
    if not search_file:
        raise HTTPException(status_code=400, detail="search-history.json not found in files")
    
    events = preprocess_search_history(search_file.content, request.timezone)
    return [Event(**e) for e in events]


@router.post("/subscriptions", response_model=list[Event])
async def preprocess_subs(request: PreprocessRequest):
    """
    Preprocess subscriptions.csv only.
    
    Returns list of normalized subscription events.
    """
    subs_file = None
    for f in request.files:
        if f.filename == "subscriptions.csv":
            subs_file = f
            break
    
    if not subs_file:
        raise HTTPException(status_code=400, detail="subscriptions.csv not found in files")
    
    events = preprocess_subscriptions(subs_file.content, request.timezone)
    return [Event(**e) for e in events]


@router.post("/all", response_model=PreprocessResult)
async def preprocess_all(request: PreprocessRequest):
    """
    Preprocess all files and return combined results.
    
    Processes in order: watch-history -> search-history -> subscriptions
    Returns individual results and combined events.
    """
    files_dict = [{"filename": f.filename, "content": f.content} for f in request.files]
    result = preprocess_all_files(files_dict, request.timezone)
    
    return PreprocessResult(
        watch_history=[Event(**e) for e in result["watch_history"]],
        search_history=[Event(**e) for e in result["search_history"]],
        subscriptions=[Event(**e) for e in result["subscriptions"]],
        combined_events=[Event(**e) for e in result["combined_events"]],
        stats=PreprocessStats(
            total_watch=result["stats"]["total_watch"],
            total_search=result["stats"]["total_search"],
            total_subscribe=result["stats"]["total_subscribe"],
            total_events=result["stats"]["total_events"],
            language_breakdown=LanguageBreakdown(**result["stats"]["language_breakdown"])
        ),
        timezone=request.timezone
    )


@router.post("/all-and-store", response_model=PreprocessedSessionData)
async def preprocess_and_store(request: PreprocessRequest):
    """
    Preprocess all files, combine results, and store in session.
    
    Returns session token with preprocessed events.
    """
    files_dict = [{"filename": f.filename, "content": f.content} for f in request.files]
    result = preprocess_all_files(files_dict, request.timezone)
    
    # Create session data
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    token = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"
    
    session_data = {
        "token": token,
        "events": result["combined_events"],
        "stats": result["stats"],
        "timezone": request.timezone,
        "created_at": created_at
    }
    
    # Save to file
    session_path = STORAGE_DIR / f"preprocessed_{token}.json"
    with open(session_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2)
    
    stats = PreprocessStats(
        total_watch=result["stats"]["total_watch"],
        total_search=result["stats"]["total_search"],
        total_subscribe=result["stats"]["total_subscribe"],
        total_events=result["stats"]["total_events"],
        language_breakdown=LanguageBreakdown(**result["stats"]["language_breakdown"])
    )
    
    return PreprocessedSessionData(
        token=token,
        events=[Event(**e) for e in result["combined_events"]],
        stats=stats,
        timezone=request.timezone,
        created_at=created_at
    )


@router.get("/session/{token}", response_model=PreprocessedSessionData)
async def get_preprocessed_session(token: str):
    """
    Retrieve preprocessed session data by token.
    """
    session_path = STORAGE_DIR / f"preprocessed_{token}.json"
    
    if not session_path.exists():
        raise HTTPException(status_code=404, detail="Preprocessed session not found")
    
    try:
        with open(session_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return PreprocessedSessionData(
            token=data["token"],
            events=[Event(**e) for e in data["events"]],
            stats=PreprocessStats(**data["stats"]),
            timezone=data["timezone"],
            created_at=data["created_at"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading session: {str(e)}")
