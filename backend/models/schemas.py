"""
Pydantic schemas for request/response models
"""

from typing import Optional, List
from pydantic import BaseModel


class FilePathInfo(BaseModel):
    """Information about a found file in the ZIP"""
    filename: str
    path: Optional[str] = None
    found: bool = False


class ScanResult(BaseModel):
    """Result of scanning a ZIP file for target files"""
    found_files: dict[str, Optional[str]]  # filename -> path or None
    missing_files: list[str]
    total_files_in_zip: int


class ExtractRequest(BaseModel):
    """Request to extract specific files from a ZIP"""
    paths: dict[str, str]  # filename -> path in ZIP
    timezone: str


class ExtractedFile(BaseModel):
    """Content of an extracted file"""
    filename: str
    content_type: str  # 'json' or 'csv'
    content: str  # Raw content as string
    size_bytes: int


class ExtractResult(BaseModel):
    """Result of extracting files from ZIP"""
    files: list[ExtractedFile]
    timezone: str
    missing_files: list[str]


class PreviewRequest(BaseModel):
    """Request to preview file contents"""
    files: list[ExtractedFile]
    timezone: str


class PreviewResult(BaseModel):
    """Preview of file contents for display"""
    watch_history: Optional[dict] = None
    search_history: Optional[dict] = None
    subscriptions: Optional[dict] = None
    timezone: str


class SessionStoreRequest(BaseModel):
    """Request to store extracted files in a session"""
    files: list[ExtractedFile]
    timezone: str


class SessionResponse(BaseModel):
    """Response after storing session"""
    token: str
    files_stored: list[str]
    timezone: str
    created_at: str


class SessionData(BaseModel):
    """Full session data structure"""
    token: str
    files: list[ExtractedFile]
    timezone: str
    created_at: str


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None


class Event(BaseModel):
    """Normalized event from YouTube data"""
    type: str  # "watch" | "search" | "subscribe"
    engagement: Optional[str] = None  # "active" | "passive" | None
    timestamp_utc: Optional[str] = None
    timestamp_local: Optional[str] = None  # Converted to user's timezone
    hour_local: Optional[int] = None  # Hour of day (0-23)
    day_of_week: Optional[int] = None  # Day of week (0=Monday, 6=Sunday)
    month_local: Optional[int] = None  # Month (1-12)
    text_raw: Optional[str] = None  # Original text before cleaning
    text_clean: Optional[str] = None  # Cleaned/normalized text
    language_type: Optional[str] = None  # "hindi" | "hinglish" | "english" | "unknown"
    language_confidence: Optional[str] = None  # "high" | "medium" | "low"
    # Micro topic extraction fields
    hashtags: Optional[List[str]] = None  # Extracted hashtags
    ner: Optional[List[str]] = None  # Named entities from NER
    nouns: Optional[List[str]] = None  # Extracted nouns
    text_v1: Optional[str] = None  # Hinglish only: text with Hindi removed
    micro_topics: Optional[List[str]] = None  # Aggregated & deduplicated topics
    channel: Optional[str] = None
    channel_clean: Optional[str] = None  # Lowercased channel name
    channel_url: Optional[str] = None
    video_url: Optional[str] = None  # YouTube video URL (from titleUrl)


class LanguageBreakdown(BaseModel):
    """Language detection statistics"""
    hindi: int = 0
    hinglish: int = 0
    english: int = 0
    unknown: int = 0


class PreprocessStats(BaseModel):
    """Statistics from preprocessing"""
    total_watch: int = 0
    total_search: int = 0
    total_subscribe: int = 0
    total_events: int = 0
    language_breakdown: LanguageBreakdown = LanguageBreakdown()


class PreprocessResult(BaseModel):
    """Result of preprocessing files"""
    watch_history: list[Event] = []
    search_history: list[Event] = []
    subscriptions: list[Event] = []
    combined_events: list[Event] = []
    stats: PreprocessStats
    timezone: str


class PreprocessRequest(BaseModel):
    """Request to preprocess extracted files"""
    files: list[ExtractedFile]
    timezone: str


class PreprocessedSessionData(BaseModel):
    """Session data with preprocessed events"""
    token: str
    events: list[Event]
    stats: PreprocessStats
    timezone: str
    created_at: str
