"""
Session management service
Handles storing and retrieving session data locally
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path


# Storage directory for sessions
STORAGE_DIR = Path(__file__).parent.parent / "storage"


def _ensure_storage_dir():
    """Ensure the storage directory exists"""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _get_session_path(token: str) -> Path:
    """Get the file path for a session"""
    return STORAGE_DIR / f"{token}.json"


def create_session(files: list[dict], timezone: str) -> dict:
    """
    Create a new session and store files locally.
    
    Args:
        files: List of extracted file dictionaries
        timezone: User's timezone
        
    Returns:
        Session response with token and metadata
    """
    _ensure_storage_dir()
    
    token = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"
    
    session_data = {
        "token": token,
        "files": files,
        "timezone": timezone,
        "created_at": created_at
    }
    
    # Save to file
    session_path = _get_session_path(token)
    with open(session_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2)
    
    return {
        "token": token,
        "files_stored": [f["filename"] for f in files],
        "timezone": timezone,
        "created_at": created_at
    }


def get_session(token: str) -> Optional[dict]:
    """
    Retrieve session data by token.
    
    Args:
        token: Session token
        
    Returns:
        Session data or None if not found
    """
    session_path = _get_session_path(token)
    
    if not session_path.exists():
        return None
    
    try:
        with open(session_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def delete_session(token: str) -> bool:
    """
    Delete a session by token.
    
    Args:
        token: Session token
        
    Returns:
        True if deleted, False if not found
    """
    session_path = _get_session_path(token)
    
    if not session_path.exists():
        return False
    
    try:
        os.remove(session_path)
        return True
    except OSError:
        return False


def list_sessions() -> list[dict]:
    """
    List all sessions (for debugging).
    
    Returns:
        List of session metadata
    """
    _ensure_storage_dir()
    
    sessions = []
    for session_file in STORAGE_DIR.glob("*.json"):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sessions.append({
                    "token": data.get("token"),
                    "files_stored": [f["filename"] for f in data.get("files", [])],
                    "timezone": data.get("timezone"),
                    "created_at": data.get("created_at")
                })
        except (json.JSONDecodeError, IOError):
            continue
    
    return sessions


def cleanup_expired_sessions(max_age_hours: int = 24) -> int:
    """
    Remove sessions older than max_age_hours.
    
    Args:
        max_age_hours: Maximum age in hours
        
    Returns:
        Number of sessions deleted
    """
    _ensure_storage_dir()
    
    deleted_count = 0
    now = datetime.utcnow()
    
    for session_file in STORAGE_DIR.glob("*.json"):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                created_at_str = data.get("created_at", "")
                
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.rstrip('Z'))
                    age_hours = (now - created_at).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        os.remove(session_file)
                        deleted_count += 1
        except (json.JSONDecodeError, IOError, ValueError):
            continue
    
    return deleted_count
