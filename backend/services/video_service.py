"""
Video Category Scraper
Extracts video category from YouTube video pages
"""

import re
import json
import requests
from typing import Optional


def extract_video_id(video_url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    if not video_url:
        return None
    
    # Pattern for watch?v=ID
    match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', video_url)
    if match:
        return match.group(1)
    
    # Pattern for youtu.be/ID
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', video_url)
    if match:
        return match.group(1)
    
    # Pattern for embed/ID
    match = re.search(r'/embed/([a-zA-Z0-9_-]{11})', video_url)
    if match:
        return match.group(1)
    
    return None


def fetch_html(video_url: str) -> Optional[str]:
    """Fetch HTML content from YouTube video page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        response = requests.get(video_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching HTML: {e}")
        return None


def extract_player_response(html: str) -> Optional[dict]:
    """Extract ytInitialPlayerResponse JSON from HTML."""
    if not html:
        return None
    
    try:
        # Look for ytInitialPlayerResponse in the HTML
        pattern = r'var ytInitialPlayerResponse\s*=\s*(\{.+?\});'
        match = re.search(pattern, html)
        
        if not match:
            # Try alternative pattern
            pattern = r'ytInitialPlayerResponse\s*=\s*(\{.+?\});'
            match = re.search(pattern, html)
        
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None
    except Exception as e:
        print(f"Error extracting player response: {e}")
        return None


def get_video_category(video_url: str) -> Optional[str]:
    """
    Get video category from YouTube video URL.
    
    Args:
        video_url: YouTube video URL (e.g., https://www.youtube.com/watch?v=xxx)
    
    Returns:
        Category string (e.g., "Science & Technology", "Entertainment", "Music")
        or None if not found
    """
    try:
        html = fetch_html(video_url)
        if not html:
            return None
        
        data = extract_player_response(html)
        if not data:
            return None
        
        # Extract category from microformat
        category = (
            data.get("microformat", {})
                .get("playerMicroformatRenderer", {})
                .get("category")
        )
        
        return category
    except Exception as e:
        print(f"Error getting video category: {e}")
        return None


def get_video_metadata(video_url: str) -> dict:
    """
    Get full video metadata from YouTube video URL.
    
    Returns dict with:
    - video_id
    - category
    - title
    - channel_name
    - description (truncated)
    - keywords
    """
    result = {
        "video_id": None,
        "category": None,
        "title": None,
        "channel_name": None,
        "description": None,
        "keywords": [],
        "error": None
    }
    
    try:
        video_id = extract_video_id(video_url)
        result["video_id"] = video_id
        
        html = fetch_html(video_url)
        if not html:
            result["error"] = "Failed to fetch HTML"
            return result
        
        data = extract_player_response(html)
        if not data:
            result["error"] = "Failed to parse player response"
            return result
        
        # Extract from microformat
        microformat = data.get("microformat", {}).get("playerMicroformatRenderer", {})
        result["category"] = microformat.get("category")
        result["title"] = microformat.get("title", {}).get("simpleText")
        result["channel_name"] = microformat.get("ownerChannelName")
        
        # Get description (truncated)
        desc = microformat.get("description", {}).get("simpleText", "")
        result["description"] = desc[:500] if desc else None
        
        # Get keywords from videoDetails
        video_details = data.get("videoDetails", {})
        result["keywords"] = video_details.get("keywords", [])
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


# Test function
if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"Testing with: {test_url}")
    
    print("\n--- Simple category extraction ---")
    category = get_video_category(test_url)
    print(f"Category: {category}")
    
    print("\n--- Full metadata ---")
    metadata = get_video_metadata(test_url)
    print(json.dumps(metadata, indent=2))
