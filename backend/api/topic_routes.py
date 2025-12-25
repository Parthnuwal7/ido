"""
API routes for topic extraction v2.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from pathlib import Path
import json

from services.micro_topic_service import (
    extract_micro_topics_v2,
    process_events_batch,
    get_aggregated_topics,
    extract_hashtags
)

topic_router = APIRouter(prefix="/api/topics", tags=["Topics"])


class ExtractRequest(BaseModel):
    text: str
    language_type: str = "english"


class ExtractResponse(BaseModel):
    text: str
    language_type: str
    hashtags: List[str]
    ner: List[str]
    nouns: List[str]
    text_v1: Optional[str] = None
    micro_topics: List[str]


@topic_router.post("/extract", response_model=ExtractResponse)
async def extract_topics_single(request: ExtractRequest):
    """
    Extract micro topics from a single text.
    
    Useful for testing the extraction pipeline.
    """
    # Create a mock event to use the extraction function
    mock_event = {
        "type": "watch",
        "engagement": "active",
        "text_clean": request.text,
        "language_type": request.language_type
    }
    
    # Process it
    result = extract_micro_topics_v2(mock_event)
    
    return ExtractResponse(
        text=request.text,
        language_type=request.language_type,
        hashtags=result.get("hashtags", []),
        ner=result.get("ner", []),
        nouns=result.get("nouns", []),
        text_v1=result.get("text_v1"),
        micro_topics=result.get("micro_topics", [])
    )


@topic_router.post("/{token}/enrich")
async def enrich_session_topics(token: str):
    """
    Enrich all events in a session with micro topics.
    
    Only processes events with type=watch and engagement=active.
    Adds hashtags, ner, nouns, text_v1, and micro_topics fields.
    """
    storage_dir = Path("storage")
    file_path = storage_dir / f"preprocessed_{token}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Load events
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    events = data.get("events", [])
    
    # Count qualifying events before processing
    active_watch_count = sum(
        1 for e in events 
        if e.get("type") == "watch" and e.get("engagement") == "active"
    )
    
    # Process events
    processed_events = process_events_batch(events)
    
    # Count results
    events_with_topics = sum(1 for e in processed_events if e.get("micro_topics"))
    total_topics = sum(len(e.get("micro_topics", [])) for e in processed_events)
    total_hashtags = sum(len(e.get("hashtags", [])) for e in processed_events)
    total_ner = sum(len(e.get("ner", [])) for e in processed_events)
    total_nouns = sum(len(e.get("nouns", [])) for e in processed_events)
    
    # Save updated data
    data["events"] = processed_events
    data["micro_topics_extracted"] = True
    data["extraction_version"] = "v2"
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {
        "token": token,
        "total_events": len(events),
        "active_watch_events": active_watch_count,
        "events_with_topics": events_with_topics,
        "extraction_stats": {
            "total_hashtags": total_hashtags,
            "total_ner": total_ner,
            "total_nouns": total_nouns,
            "total_micro_topics": total_topics
        },
        "status": "enriched"
    }


@topic_router.get("/{token}/aggregate")
async def get_session_topics(token: str, top_n: int = 50):
    """
    Get aggregated micro topics for a session.
    
    Returns:
    - top_hashtags: Most common hashtags
    - top_ner: Most common named entities
    - top_nouns: Most common nouns
    - top_micro_topics: Most common overall
    """
    storage_dir = Path("storage")
    file_path = storage_dir / f"preprocessed_{token}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Load events
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    events = data.get("events", [])
    
    # Check if topics are extracted
    if not data.get("micro_topics_extracted"):
        raise HTTPException(
            status_code=400, 
            detail="Topics not extracted yet. Call POST /{token}/enrich first."
        )
    
    # Aggregate topics
    aggregated = get_aggregated_topics(events, top_n)
    
    # Add language breakdown
    from collections import Counter
    language_topics = {"english": [], "hindi": [], "hinglish": [], "unknown": []}
    
    for event in events:
        if event.get("type") == "watch" and event.get("engagement") == "active":
            lang = event.get("language_type", "unknown")
            topics = event.get("micro_topics", [])
            if lang in language_topics:
                language_topics[lang].extend(topics)
    
    language_breakdown = {
        lang: [{"topic": t, "count": c} for t, c in Counter(topics).most_common(20)]
        for lang, topics in language_topics.items()
        if topics  # Only include languages with topics
    }
    
    return {
        "token": token,
        "version": data.get("extraction_version", "v1"),
        "stats": aggregated["stats"],
        "top_hashtags": aggregated["top_hashtags"],
        "top_ner": aggregated["top_ner"],
        "top_nouns": aggregated["top_nouns"],
        "top_micro_topics": aggregated["top_micro_topics"],
        "by_language": language_breakdown
    }
