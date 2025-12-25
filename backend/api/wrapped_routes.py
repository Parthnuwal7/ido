"""
Wrapped API Routes
Stateless endpoint for generating YouTube Wrapped cards.

Uses the same preprocessing as admin analytics for consistency.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import zipfile
import json
import io

from services.wrapped_service import generate_wrapped_cards
from services.preprocess_service import (
    preprocess_watch_history,
    preprocess_search_history,
    preprocess_subscriptions
)

wrapped_router = APIRouter(prefix="/api/wrapped", tags=["Wrapped"])


@wrapped_router.post("/generate")
async def generate_wrapped(
    file: UploadFile = File(...),
    timezone: str = Form(default="UTC")
):
    """
    Generate YouTube Wrapped cards from a takeout ZIP file.
    
    This is a stateless endpoint - no data is stored on the server.
    Uses the same preprocessing as admin analytics for consistency.
    
    Args:
        file: YouTube takeout ZIP file
        timezone: User's timezone (e.g., "Asia/Kolkata", "America/New_York")
    
    Returns:
        JSON with all card data for rendering the wrapped experience
    """
    # Validate file type
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    try:
        # Read ZIP file into memory
        content = await file.read()
        
        # Process in memory using existing preprocess functions
        events, stats = await process_zip_in_memory(content, timezone)
        
        if not events:
            raise HTTPException(status_code=400, detail="No valid events found in ZIP")
        
        # Generate card data
        cards = generate_wrapped_cards(events, stats)
        
        if "error" in cards:
            raise HTTPException(status_code=400, detail=cards["error"])
        
        return JSONResponse(content=cards)
        
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except Exception as e:
        print(f"[ERROR] Wrapped generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


async def process_zip_in_memory(content: bytes, timezone: str) -> tuple:
    """
    Process a YouTube takeout ZIP file entirely in memory.
    Uses the SAME preprocessing functions as admin analytics.
    
    Args:
        content: ZIP file bytes
        timezone: User timezone string
    
    Returns:
        Tuple of (events list, stats dict)
    """
    events = []
    stats = {
        "total_events": 0,
        "total_watch": 0,
        "total_search": 0,
        "total_subscribe": 0,
        "language_breakdown": {"english": 0, "hindi": 0, "hinglish": 0, "unknown": 0}
    }
    
    # Open ZIP from bytes
    with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_ref:
        file_list = zip_ref.namelist()
        
        print(f"[DEBUG] Found {len(file_list)} files in ZIP")
        
        # Find relevant files
        watch_history_file = None
        search_history_file = None
        subscriptions_file = None
        
        for f in file_list:
            basename = f.split('/')[-1].lower()
            
            if basename == 'watch-history.json':
                watch_history_file = f
                print(f"[DEBUG] Found watch history: {f}")
            elif basename == 'search-history.json':
                search_history_file = f
                print(f"[DEBUG] Found search history: {f}")
            elif basename == 'subscriptions.csv':
                subscriptions_file = f
                print(f"[DEBUG] Found subscriptions: {f}")
        
        # Process watch history using existing function
        if watch_history_file:
            try:
                with zip_ref.open(watch_history_file) as f:
                    content_str = f.read().decode('utf-8')
                    print(f"[DEBUG] Read {len(content_str)} bytes from watch history")
                    
                    # Use the SAME preprocess function as admin
                    watch_events = preprocess_watch_history(content_str, timezone)
                    events.extend(watch_events)
                    stats["total_watch"] = len(watch_events)
                    print(f"[DEBUG] Processed {len(watch_events)} watch events")
            except Exception as e:
                print(f"[ERROR] Processing watch history: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("[DEBUG] No watch history file found!")
        
        # Process search history using existing function
        if search_history_file:
            try:
                with zip_ref.open(search_history_file) as f:
                    content_str = f.read().decode('utf-8')
                    
                    # Use the SAME preprocess function as admin
                    search_events = preprocess_search_history(content_str, timezone)
                    events.extend(search_events)
                    stats["total_search"] = len(search_events)
                    print(f"[DEBUG] Processed {len(search_events)} search events")
            except Exception as e:
                print(f"[ERROR] Processing search history: {e}")
        
        # Process subscriptions using existing function
        if subscriptions_file:
            try:
                with zip_ref.open(subscriptions_file) as f:
                    content_str = f.read().decode('utf-8')
                    
                    # Use the SAME preprocess function as admin
                    sub_events = preprocess_subscriptions(content_str, timezone)
                    events.extend(sub_events)
                    stats["total_subscribe"] = len(sub_events)
                    print(f"[DEBUG] Processed {len(sub_events)} subscription events")
            except Exception as e:
                print(f"[ERROR] Processing subscriptions: {e}")
    
    # Count language breakdown
    for e in events:
        lang = e.get("language_type", "unknown")
        if lang in stats["language_breakdown"]:
            stats["language_breakdown"][lang] += 1
    
    stats["total_events"] = len(events)
    
    return events, stats
