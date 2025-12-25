"""
Analytics API routes
Endpoints for analyzing preprocessed session data
"""

from fastapi import APIRouter, HTTPException
from services.analytics_service import (
    get_session_summary,
    get_channel_analytics,
    get_watch_patterns,
    get_search_analytics,
    get_subscription_overlap,
    get_full_analytics,
    get_habit_formation,
    get_temporal_trends
)

router = APIRouter()


@router.get("/{token}/summary")
async def analytics_summary(token: str):
    """Get session summary stats."""
    result = get_session_summary(token)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{token}/channels")
async def analytics_channels(token: str, top_n: int = 20, engagement: str = "all"):
    """Get channel analytics with top N channels. engagement: 'all' | 'watch' (active) | 'view' (passive)"""
    result = get_channel_analytics(token, top_n, engagement)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{token}/watch-patterns")
async def analytics_watch_patterns(token: str):
    """Get watch time patterns (hourly/daily)."""
    result = get_watch_patterns(token)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{token}/searches")
async def analytics_searches(token: str, top_n: int = 20):
    """Get search analytics."""
    result = get_search_analytics(token, top_n)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{token}/subscription-overlap")
async def analytics_subscription_overlap(token: str):
    """Get subscription vs watch overlap analysis."""
    result = get_subscription_overlap(token)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{token}/habits")
async def analytics_habits(token: str, min_streak_days: int = 3):
    """Get habit formation analytics - channels and content watched daily."""
    result = get_habit_formation(token, min_streak_days)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{token}/temporal-trends")
async def analytics_temporal_trends(token: str):
    """Get month-by-month analysis of how peak watching times change."""
    result = get_temporal_trends(token)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{token}/full")
async def analytics_full(token: str):
    """Get all analytics in one call."""
    result = get_full_analytics(token)
    if "error" in result.get("summary", {}):
        raise HTTPException(status_code=404, detail=result["summary"]["error"])
    return result
