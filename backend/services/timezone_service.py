"""
Timezone handling utilities
"""

from datetime import datetime
from typing import Optional
import pytz


def get_available_timezones() -> list[str]:
    """
    Get list of all available timezone names.
    
    Returns:
        Sorted list of timezone names
    """
    return sorted(pytz.all_timezones)


def get_common_timezones() -> list[str]:
    """
    Get list of common timezone names.
    
    Returns:
        List of common timezone names
    """
    return sorted(pytz.common_timezones)


def validate_timezone(timezone: str) -> bool:
    """
    Check if a timezone string is valid.
    
    Args:
        timezone: Timezone string (e.g., 'America/New_York')
        
    Returns:
        True if valid, False otherwise
    """
    try:
        pytz.timezone(timezone)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


def convert_utc_to_local(utc_datetime: datetime, timezone: str) -> Optional[datetime]:
    """
    Convert a UTC datetime to local time.
    
    Args:
        utc_datetime: Datetime in UTC
        timezone: Target timezone string
        
    Returns:
        Datetime in local timezone, or None if conversion fails
    """
    try:
        tz = pytz.timezone(timezone)
        utc = pytz.UTC.localize(utc_datetime) if utc_datetime.tzinfo is None else utc_datetime
        return utc.astimezone(tz)
    except Exception:
        return None


def parse_youtube_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse a YouTube timestamp string to datetime.
    YouTube timestamps are typically in ISO 8601 format.
    
    Args:
        timestamp_str: Timestamp string from YouTube data
        
    Returns:
        Parsed datetime or None if parsing fails
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    
    return None


def get_local_time_info(utc_datetime: datetime, timezone: str) -> Optional[dict]:
    """
    Get local time information for a UTC datetime.
    
    Args:
        utc_datetime: Datetime in UTC
        timezone: Target timezone string
        
    Returns:
        Dictionary with local time info
    """
    local_dt = convert_utc_to_local(utc_datetime, timezone)
    
    if local_dt is None:
        return None
    
    return {
        "timestamp_local": local_dt.isoformat(),
        "hour_local": local_dt.hour,
        "day_of_week": local_dt.weekday(),  # 0 = Monday, 6 = Sunday
        "day_name": local_dt.strftime("%A"),
        "date_local": local_dt.strftime("%Y-%m-%d")
    }
