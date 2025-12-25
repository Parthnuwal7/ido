"""
Language Detection Service
Detects Hindi, Hinglish, and English from text using Unicode ranges and dictionary-based detection.
"""

import re
from typing import Tuple

# Unicode ranges
DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F]')
LATIN_PATTERN = re.compile(r'[a-zA-Z]')

# Hinglish marker words - structural words that strongly indicate Romanized Hindi
HINGLISH_MARKERS = {
    # Conjunctions / particles
    "aur", "ya", "lekin", "par", "toh", "bhi", "hi", "na", "nahi", "nhi",
    
    # Verbs / helpers
    "hai", "ho", "hoga", "hogi", "tha", "thi", "the", "hain",
    "kya", "kaise", "kyun", "kyu", "kyunki", "karo", "karna", "krna",
    "samjhao", "batao", "dekho", "suno", "jao", "aao", "chalo",
    
    # Postpositions
    "ka", "ki", "ke", "mein", "me", "se", "tak", "wala", "wali", "wale",
    "ko", "pe", "pr",
    
    # Question / emphasis
    "kab", "kaha", "kaun", "kitna", "sach", "jhooth", "accha", "theek",
    
    # Common high-signal nouns
    "ghar", "dost", "bhai", "yaar", "paisa", "paise", "kaam", "log",
    "rishta", "pyaar", "zindagi", "dil", "duniya",
}

# Words that are ambiguous (exist in English too) - don't count for short titles
AMBIGUOUS_MARKERS = {"me", "the", "hi", "par", "ko"}

# High-signal markers that are definitely Hinglish even in short text
HIGH_SIGNAL_MARKERS = HINGLISH_MARKERS - AMBIGUOUS_MARKERS


def has_devanagari(text: str) -> bool:
    """Check if text contains any Devanagari characters."""
    return bool(DEVANAGARI_PATTERN.search(text))


def has_latin(text: str) -> bool:
    """Check if text contains any Latin characters."""
    return bool(LATIN_PATTERN.search(text))


def tokenize_for_detection(text: str) -> list[str]:
    """
    Tokenize text for language detection.
    - Lowercase
    - Remove punctuation and numbers
    - Split by whitespace
    """
    if not text:
        return []
    
    # Lowercase
    text = text.lower()
    
    # Remove non-alphabetic characters (keep spaces)
    text = re.sub(r'[^a-z\s]', '', text)
    
    # Split and filter empty
    words = [w.strip() for w in text.split() if w.strip()]
    
    return words


def count_hinglish_markers(words: list[str]) -> int:
    """Count how many words match Hinglish markers."""
    return sum(1 for word in words if word in HINGLISH_MARKERS)


def count_high_signal_markers(words: list[str]) -> int:
    """Count how many words match high-signal (non-ambiguous) Hinglish markers."""
    return sum(1 for word in words if word in HIGH_SIGNAL_MARKERS)


def detect_language(text: str) -> Tuple[str, str]:
    """
    Detect language type and confidence from text.
    
    Returns:
        Tuple of (language_type, confidence)
        - language_type: "hindi" | "hinglish" | "english" | "unknown"
        - confidence: "high" | "medium" | "low"
    
    Algorithm:
    1. Check for Devanagari vs Latin script presence
    2. If mixed scripts → hinglish (high)
    3. If pure Devanagari → hindi (high)
    4. If only Latin → check for Hinglish markers
    5. For short titles (< 3 words), only count high-signal markers
    6. Apply confidence based on marker count
    """
    if not text or len(text.strip()) < 3:
        return ("unknown", "low")
    
    text = text.strip()
    
    has_dev = has_devanagari(text)
    has_lat = has_latin(text)
    
    # If no letters at all (just numbers/punctuation), treat as English
    if not has_dev and not has_lat:
        return ("english", "high")
    
    # Step 1: Script-based detection
    
    # Pure Devanagari (no Latin letters)
    if has_dev and not has_lat:
        return ("hindi", "high")
    
    # Mixed scripts (Devanagari + Latin)
    if has_dev and has_lat:
        return ("hinglish", "high")
    
    # Step 2: Only Latin script - check for Hinglish markers
    if has_lat and not has_dev:
        words = tokenize_for_detection(text)
        total_words = len(words)
        
        if total_words == 0:
            return ("unknown", "low")
        
        hinglish_hits = count_hinglish_markers(words)
        high_signal_hits = count_high_signal_markers(words)
        
        # Decision rules
        if hinglish_hits >= 2:
            # 2+ markers is strong signal regardless of text length
            return ("hinglish", "high")
        
        if hinglish_hits == 1:
            # Only 1 marker - must be a high-signal marker (not ambiguous)
            # This prevents "the", "me", "hi" etc. from triggering false positives
            if high_signal_hits >= 1:
                if total_words >= 3:
                    return ("hinglish", "medium")
                else:
                    # Short text with high-signal marker
                    return ("hinglish", "medium")
            else:
                # Only ambiguous marker(s) found - treat as English
                return ("english", "high")
        
        # No Hinglish markers found
        return ("english", "high")
    
    # Fallback (shouldn't reach here normally)
    return ("unknown", "low")


def detect_language_with_details(text: str) -> dict:
    """
    Detect language with additional debug details.
    
    Returns dict with:
    - language_type
    - language_confidence
    - has_devanagari
    - has_latin
    - hinglish_marker_count
    - total_words
    """
    if not text:
        return {
            "language_type": "unknown",
            "language_confidence": "low",
            "has_devanagari": False,
            "has_latin": False,
            "hinglish_marker_count": 0,
            "total_words": 0
        }
    
    has_dev = has_devanagari(text)
    has_lat = has_latin(text)
    words = tokenize_for_detection(text)
    hinglish_hits = count_hinglish_markers(words)
    
    lang_type, confidence = detect_language(text)
    
    return {
        "language_type": lang_type,
        "language_confidence": confidence,
        "has_devanagari": has_dev,
        "has_latin": has_lat,
        "hinglish_marker_count": hinglish_hits,
        "total_words": len(words)
    }
