"""
Channel Metadata Service
Extracts channel information from YouTube channel URLs using yt-dlp
"""

import yt_dlp
from typing import Optional
import re


def extract_channel_id(channel_url: str) -> Optional[str]:
    """Extract channel ID from various YouTube URL formats."""
    if not channel_url:
        return None
    
    # Pattern for /channel/ID format
    match = re.search(r'/channel/([a-zA-Z0-9_-]+)', channel_url)
    if match:
        return match.group(1)
    
    # Pattern for /@handle format
    match = re.search(r'/@([a-zA-Z0-9_-]+)', channel_url)
    if match:
        return f"@{match.group(1)}"
    
    return None


def get_channel_metadata(channel_url: str) -> dict:
    """
    Get channel metadata from YouTube channel URL.
    
    Args:
        channel_url: YouTube channel URL (e.g., https://www.youtube.com/channel/UCxxx)
    
    Returns:
        Dictionary with channel metadata
    """
    result = {
        "channel_id": None,
        "channel_name": None,
        "channel_description": None,
        "subscriber_count": None,
        "video_count": None,
        "keywords": [],
        "category": None,
        "error": None
    }
    
    if not channel_url:
        result["error"] = "No channel URL provided"
        return result
    
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract channel info
            info = ydl.extract_info(channel_url, download=False)
            
            if info:
                result["channel_id"] = info.get("channel_id") or info.get("id")
                result["channel_name"] = info.get("channel") or info.get("uploader")
                result["channel_description"] = info.get("description")
                result["subscriber_count"] = info.get("channel_follower_count")
                result["keywords"] = info.get("tags", [])
                
                # Try to get video count from entries
                entries = info.get("entries", [])
                if entries:
                    result["video_count"] = len(entries)
                
    except Exception as e:
        result["error"] = str(e)
    
    return result


def get_channels_metadata_batch(channel_urls: list[str]) -> dict:
    """
    Get metadata for multiple channels.
    
    Args:
        channel_urls: List of unique channel URLs
    
    Returns:
        Dictionary mapping channel_url to metadata
    """
    results = {}
    
    for url in channel_urls:
        if url and url not in results:
            results[url] = get_channel_metadata(url)
    
    return results


# Quick test function
if __name__ == "__main__":
    test_url = "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw"
    print(f"Testing with: {test_url}")
    result = get_channel_metadata(test_url)
    print(result)
