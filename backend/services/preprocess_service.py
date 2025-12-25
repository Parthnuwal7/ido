"""
Data preprocessing service
Transforms raw YouTube Takeout data into normalized Event format
"""

import re
import json
import csv
import io
from typing import Optional
from datetime import datetime
import pytz

from services.language_service import detect_language


def clean_text(text: str) -> str:
    """
    Clean text by:
    - Removing prefixes (Watched, Viewed, Searched for)
    - Lowercasing
    - Removing emojis
    - Removing URLs
    """
    if not text:
        return ""
    
    # Remove common prefixes
    prefixes = [
        "Watched ", "Viewed ", "Searched for ",
        "watched ", "viewed ", "searched for "
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove emojis (Unicode emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    
    # Lowercase and strip
    text = text.lower().strip()
    
    return text


def parse_timestamp(time_str: str) -> Optional[str]:
    """Parse YouTube timestamp to ISO format (UTC)"""
    if not time_str:
        return None
    
    try:
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.isoformat() + "Z"
            except ValueError:
                continue
        
        return time_str
    except Exception:
        return None


def convert_to_local_time(utc_time_str: str, timezone_str: str) -> dict:
    """
    Convert UTC timestamp to local timezone and extract time components.
    
    Args:
        utc_time_str: ISO format UTC timestamp (ending with Z)
        timezone_str: Timezone string like "Asia/Kolkata"
    
    Returns:
        Dict with timestamp_local, hour_local, day_of_week, month_local, or all None if conversion fails
    """
    result = {
        "timestamp_local": None,
        "hour_local": None,
        "day_of_week": None,
        "month_local": None
    }
    
    if not utc_time_str or not timezone_str:
        return result
    
    try:
        # Parse UTC time
        utc_time_str = utc_time_str.rstrip('Z')
        
        # Try different formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ]
        
        dt_utc = None
        for fmt in formats:
            try:
                dt_utc = datetime.strptime(utc_time_str, fmt)
                break
            except ValueError:
                continue
        
        if dt_utc is None:
            return result
        
        # Make it timezone-aware (UTC)
        dt_utc = pytz.UTC.localize(dt_utc)
        
        # Convert to target timezone
        target_tz = pytz.timezone(timezone_str)
        dt_local = dt_utc.astimezone(target_tz)
        
        # Extract components
        result["timestamp_local"] = dt_local.isoformat()
        result["hour_local"] = dt_local.hour  # 0-23
        result["day_of_week"] = dt_local.weekday()  # 0=Monday, 6=Sunday
        result["month_local"] = dt_local.month  # 1-12
        
        return result
        
    except Exception:
        return None


def is_google_ads(entry: dict) -> bool:
    """Check if entry is from Google Ads"""
    details = entry.get("details", [])
    for detail in details:
        if detail.get("name") == "From Google Ads":
            return True
    return False


def is_youtube_post(entry: dict) -> bool:
    """Check if entry is a YouTube post (not a video)"""
    title_url = entry.get("titleUrl", "")
    if "/post/" in title_url:
        return True
    return False


def get_engagement(title: str) -> str:
    """Determine engagement type from title prefix"""
    if not title:
        return "passive"
    
    if title.startswith("Watched"):
        return "active"
    return "passive"


def enrich_event_with_language(event: dict) -> dict:
    """Add language detection to an event based on text_clean."""
    text = event.get("text_clean")
    
    if text:
        lang_type, lang_confidence = detect_language(text)
        event["language_type"] = lang_type
        event["language_confidence"] = lang_confidence
    else:
        event["language_type"] = "unknown"
        event["language_confidence"] = "low"
    
    return event


def enrich_event_with_local_time(event: dict, timezone: str) -> dict:
    """Add local timestamp and time components to an event."""
    timestamp_utc = event.get("timestamp_utc")
    
    time_data = convert_to_local_time(timestamp_utc, timezone)
    event["timestamp_local"] = time_data["timestamp_local"]
    event["hour_local"] = time_data["hour_local"]
    event["day_of_week"] = time_data["day_of_week"]
    event["month_local"] = time_data["month_local"]
    
    return event


def preprocess_watch_history(content: str, timezone: str = "UTC") -> list[dict]:
    """
    Process watch-history.json into normalized Event format.
    
    Rules:
    1. Drop Google Ads entries
    2. Drop YouTube post entries
    3. Tag engagement based on "Watched" prefix
    4. Clean title text
    5. Extract channel info from subtitles
    6. Detect language
    7. Convert timestamp to local
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    
    if not isinstance(data, list):
        return []
    
    events = []
    
    for entry in data:
        # Skip Google Ads
        if is_google_ads(entry):
            continue
        
        # Skip YouTube posts
        if is_youtube_post(entry):
            continue
        
        title = entry.get("title", "")
        
        # Determine engagement
        engagement = get_engagement(title)
        
        # Get raw text (after removing "Watched" prefix)
        text_raw = title
        for prefix in ["Watched ", "Viewed "]:
            if text_raw.startswith(prefix):
                text_raw = text_raw[len(prefix):]
                break
        
        # Clean title text
        text_clean = clean_text(title)
        
        # Extract channel info from subtitles
        channel = None
        channel_url = None
        subtitles = entry.get("subtitles", [])
        if subtitles and len(subtitles) > 0:
            channel = subtitles[0].get("name")
            channel_url = subtitles[0].get("url")
        
        # Get video URL from titleUrl
        video_url = entry.get("titleUrl")
        
        # Get timestamp
        timestamp_utc = parse_timestamp(entry.get("time"))
        
        event = {
            "type": "watch",
            "engagement": engagement,
            "timestamp_utc": timestamp_utc,
            "timestamp_local": None,
            "hour_local": None,
            "day_of_week": None,
            "month_local": None,
            "text_raw": text_raw if text_raw else None,
            "text_clean": text_clean if text_clean else None,
            "language_type": None,
            "language_confidence": None,
            "channel": channel,
            "channel_clean": channel.lower() if channel else None,
            "channel_url": channel_url,
            "video_url": video_url
        }
        
        # Enrich with language detection
        event = enrich_event_with_language(event)
        
        # Enrich with local time
        event = enrich_event_with_local_time(event, timezone)
        
        events.append(event)
    
    return events


def preprocess_search_history(content: str, timezone: str = "UTC") -> list[dict]:
    """
    Process search-history.json into normalized Event format.
    
    Rules:
    1. Extract timestamp from "time" field
    2. Remove "Searched for" prefix from title
    3. Detect language
    4. Convert timestamp to local
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    
    if not isinstance(data, list):
        return []
    
    events = []
    
    for entry in data:
        title = entry.get("title", "")
        
        # Get raw text (after removing "Searched for" prefix)
        text_raw = title
        if text_raw.startswith("Searched for "):
            text_raw = text_raw[len("Searched for "):]
        
        # Clean title - remove "Searched for" prefix
        text_clean = clean_text(title)
        
        # Get timestamp
        timestamp_utc = parse_timestamp(entry.get("time"))
        
        event = {
            "type": "search",
            "engagement": None,
            "timestamp_utc": timestamp_utc,
            "timestamp_local": None,
            "hour_local": None,
            "day_of_week": None,
            "month_local": None,
            "text_raw": text_raw if text_raw else None,
            "text_clean": text_clean if text_clean else None,
            "language_type": None,
            "language_confidence": None,
            "channel": None,
            "channel_clean": None,
            "channel_url": None,
            "video_url": None
        }
        
        # Enrich with language detection
        event = enrich_event_with_language(event)
        
        # Enrich with local time
        event = enrich_event_with_local_time(event, timezone)
        
        events.append(event)
    
    return events


def preprocess_subscriptions(content: str, timezone: str = "UTC") -> list[dict]:
    """
    Process subscriptions.csv into normalized Event format.
    
    Rules:
    1. "Channel Title" -> channel
    2. "Channel Url" -> channel_url
    3. No text field, so no language detection needed
    """
    events = []
    
    try:
        reader = csv.DictReader(io.StringIO(content))
        
        for row in reader:
            channel = row.get("Channel Title") or row.get("Channel Id")
            channel_url = row.get("Channel Url")
            
            event = {
                "type": "subscribe",
                "engagement": None,
                "timestamp_utc": None,
                "timestamp_local": None,
                "hour_local": None,
                "day_of_week": None,
                "month_local": None,
                "text_raw": None,
                "text_clean": None,
                "language_type": None,
                "language_confidence": None,
                "channel": channel,
                "channel_clean": channel.lower() if channel else None,
                "channel_url": channel_url,
                "video_url": None
            }
            
            events.append(event)
            
    except Exception:
        return []
    
    return events


def preprocess_all_files(files: list[dict], timezone: str = "UTC") -> dict:
    """
    Process all files and combine results.
    
    Args:
        files: List of extracted file dicts with 'filename' and 'content'
        timezone: User's timezone for timestamp conversion
        
    Returns:
        Dictionary with individual results and combined events
    """
    results = {
        "watch_history": [],
        "search_history": [],
        "subscriptions": [],
        "combined_events": [],
        "stats": {
            "total_watch": 0,
            "total_search": 0,
            "total_subscribe": 0,
            "total_events": 0,
            "language_breakdown": {
                "hindi": 0,
                "hinglish": 0,
                "english": 0,
                "unknown": 0
            }
        }
    }
    
    for file in files:
        filename = file.get("filename", "")
        content = file.get("content", "")
        
        if filename == "watch-history.json":
            events = preprocess_watch_history(content, timezone)
            results["watch_history"] = events
            results["stats"]["total_watch"] = len(events)
            results["combined_events"].extend(events)
            
        elif filename == "search-history.json":
            events = preprocess_search_history(content, timezone)
            results["search_history"] = events
            results["stats"]["total_search"] = len(events)
            results["combined_events"].extend(events)
            
        elif filename == "subscriptions.csv":
            events = preprocess_subscriptions(content, timezone)
            results["subscriptions"] = events
            results["stats"]["total_subscribe"] = len(events)
            results["combined_events"].extend(events)
    
    # Calculate language breakdown
    for event in results["combined_events"]:
        lang = event.get("language_type", "unknown")
        if lang in results["stats"]["language_breakdown"]:
            results["stats"]["language_breakdown"][lang] += 1
    
    results["stats"]["total_events"] = len(results["combined_events"])
    
    return results
