"""
Wrapped Service
Generates card JSON for YouTube Wrapped from events (in-memory, no storage).
Based on cards_doc.md specification.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re


def generate_wrapped_cards(events: List[Dict], stats: Dict) -> Dict:
    """
    Generate all card data from preprocessed events.
    
    This is the main entry point - processes events and returns
    structured JSON matching the cards in cards_doc.md.
    
    Args:
        events: List of preprocessed event dictionaries
        stats: Stats dictionary from preprocessing
    
    Returns:
        Dictionary with all card data
    """
    # Filter watch events
    watch_events = [e for e in events if e.get("type") == "watch"]
    search_events = [e for e in events if e.get("type") == "search"]
    subscribe_events = [e for e in events if e.get("type") == "subscribe"]
    
    if not watch_events:
        return {"error": "No watch events found"}
    
    # Generate each card section
    cards = {
        "intro": generate_intro_card(stats),
        "stats_overview": generate_stats_overview(events, stats, watch_events),
        "time_spent": generate_time_spent_card(watch_events),
        "peak_month": generate_peak_month_card(watch_events),
        "top_channel": generate_top_channel_card(watch_events),
        "top_channels": generate_top_channels_card(watch_events),
        "watch_cycle": generate_watch_cycle_card(watch_events),
        "peak_day": generate_peak_day_card(watch_events),
        "longest_streak": generate_longest_streak_card(watch_events),
        "personality": generate_personality_card(),  # Hardcoded for now
        "binge_sessions": generate_binge_sessions_card(watch_events),
        "late_night": generate_late_night_card(watch_events),
        "habits": generate_habits_card(watch_events),
        "patterns": generate_patterns_card(watch_events),  # NEW: Association rule patterns
        "rewatched": generate_rewatched_card(watch_events),
        "subscriptions": generate_subscriptions_card(watch_events, subscribe_events),
        "searches": generate_searches_card(search_events),
        "first_last": generate_first_last_card(watch_events),
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "total_events": len(events),
            "total_watch": len(watch_events)
        }
    }
    
    return cards


# ============================================
# INTRO CARD
# ============================================

def generate_intro_card(stats: Dict) -> Dict:
    """Generate intro card data."""
    return {
        "username": "there",  # Could be extracted from data if available
        "year": datetime.now().year
    }


# ============================================
# STATS OVERVIEW CARD
# ============================================

def generate_stats_overview(events: List[Dict], stats: Dict, watch_events: List[Dict]) -> Dict:
    """Generate stats overview card data."""
    # Unique channels
    channels = set(e.get("channel_clean") for e in watch_events if e.get("channel_clean"))
    
    # Active days
    active_days = set()
    for e in watch_events:
        ts = e.get("timestamp_local") or e.get("timestamp_utc")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                active_days.add(dt.date())
            except:
                pass
    
    # Sessions (using 60 min break threshold)
    sessions = count_sessions(watch_events, break_threshold_minutes=60)
    
    return {
        "videos_watched": len(watch_events),
        "channels_explored": len(channels),
        "active_days": len(active_days),
        "total_sessions": sessions
    }


# ============================================
# TIME SPENT CARD
# ============================================

def generate_time_spent_card(watch_events: List[Dict]) -> Dict:
    """Generate time spent card data."""
    time_data = compute_time_spent(watch_events)
    
    return {
        "total_hours": time_data["total_hours"],
        "total_minutes": time_data["total_minutes"],
        "avg_daily_minutes": time_data["avg_daily_minutes"]
    }


def compute_time_spent(watch_events: List[Dict], 
                       break_threshold_minutes: int = 60,
                       last_video_minutes: int = 5) -> Dict:
    """Compute approximate time spent on YouTube."""
    # Parse timestamps
    timed_events = []
    for e in watch_events:
        ts = e.get("timestamp_local") or e.get("timestamp_utc")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                timed_events.append(dt)
            except:
                pass
    
    if not timed_events:
        return {"total_hours": 0, "total_minutes": 0, "avg_daily_minutes": 0}
    
    timed_events.sort()
    
    # Detect sessions
    sessions = []
    break_threshold = timedelta(minutes=break_threshold_minutes)
    
    session_start = timed_events[0]
    session_end = timed_events[0]
    
    for i in range(1, len(timed_events)):
        gap = timed_events[i] - timed_events[i-1]
        if gap > break_threshold:
            duration = (session_end - session_start).total_seconds() / 60.0 + last_video_minutes
            sessions.append(duration)
            session_start = timed_events[i]
        session_end = timed_events[i]
    
    # Last session
    duration = (session_end - session_start).total_seconds() / 60.0 + last_video_minutes
    sessions.append(duration)
    
    total_minutes = sum(sessions)
    total_hours = round(total_minutes / 60, 1)
    
    # Unique days
    unique_days = set(dt.date() for dt in timed_events)
    avg_daily = round(total_minutes / len(unique_days), 1) if unique_days else 0
    
    return {
        "total_hours": total_hours,
        "total_minutes": round(total_minutes, 0),
        "avg_daily_minutes": avg_daily,
        "total_days": len(unique_days),
        "session_count": len(sessions)
    }


def count_sessions(watch_events: List[Dict], break_threshold_minutes: int = 60) -> int:
    """Count number of watch sessions."""
    timed_events = []
    for e in watch_events:
        ts = e.get("timestamp_local") or e.get("timestamp_utc")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                timed_events.append(dt)
            except:
                pass
    
    if not timed_events:
        return 0
    
    timed_events.sort()
    sessions = 1
    break_threshold = timedelta(minutes=break_threshold_minutes)
    
    for i in range(1, len(timed_events)):
        if timed_events[i] - timed_events[i-1] > break_threshold:
            sessions += 1
    
    return sessions


# ============================================
# PEAK MONTH CARD
# ============================================

def generate_peak_month_card(watch_events: List[Dict]) -> Dict:
    """Generate peak month card data."""
    monthly_counts = Counter()
    
    for e in watch_events:
        ts = e.get("timestamp_local") or e.get("timestamp_utc")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                month_key = dt.strftime("%B")  # Full month name
                monthly_counts[month_key] += 1
            except:
                pass
    
    if not monthly_counts:
        return {"month": "Unknown", "watches": 0}
    
    peak_month, peak_count = monthly_counts.most_common(1)[0]
    
    return {
        "month": peak_month,
        "watches": peak_count
    }


# ============================================
# TOP CHANNEL CARDS
# ============================================

def generate_top_channel_card(watch_events: List[Dict]) -> Dict:
    """Generate #1 channel spotlight card data."""
    channel_counts = Counter(
        e.get("channel_clean") for e in watch_events 
        if e.get("channel_clean")
    )
    
    if not channel_counts:
        return {"name": "Unknown", "views": 0, "percentage": 0}
    
    top_channel, top_count = channel_counts.most_common(1)[0]
    total = sum(channel_counts.values())
    percentage = round(top_count / total * 100, 1) if total > 0 else 0
    
    return {
        "name": top_channel,
        "views": top_count,
        "percentage": percentage
    }


def generate_top_channels_card(watch_events: List[Dict], top_n: int = 5) -> Dict:
    """Generate top channels list card data."""
    channel_counts = Counter(
        e.get("channel_clean") for e in watch_events 
        if e.get("channel_clean")
    )
    
    top_channels = [
        {"name": ch, "views": count}
        for ch, count in channel_counts.most_common(top_n)
    ]
    
    return {"channels": top_channels}


# ============================================
# WATCH CYCLE CARD
# ============================================

def generate_watch_cycle_card(watch_events: List[Dict]) -> Dict:
    """Generate 24-hour watch cycle card data."""
    hourly_counts = Counter()
    
    for e in watch_events:
        hour = e.get("hour_local")
        if hour is not None:
            hourly_counts[hour] += 1
    
    if not hourly_counts:
        return {"peak_hour": 12, "hourly_data": [0] * 24}
    
    peak_hour = hourly_counts.most_common(1)[0][0]
    hourly_data = [hourly_counts.get(h, 0) for h in range(24)]
    
    return {
        "peak_hour": peak_hour,
        "hourly_data": hourly_data
    }


# ============================================
# PEAK DAY CARD
# ============================================

def generate_peak_day_card(watch_events: List[Dict]) -> Dict:
    """Generate day of week card data."""
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_counts = Counter()
    
    for e in watch_events:
        day = e.get("day_of_week")
        if day is not None:
            daily_counts[day] += 1
    
    if not daily_counts:
        return {"day": "Saturday", "daily_data": {}}
    
    peak_day_num = daily_counts.most_common(1)[0][0]
    peak_day = day_names[peak_day_num] if 0 <= peak_day_num < 7 else "Saturday"
    
    daily_data = {day_names[i]: daily_counts.get(i, 0) for i in range(7)}
    
    return {
        "day": peak_day,
        "daily_data": daily_data
    }


# ============================================
# LONGEST STREAK CARD
# ============================================

def generate_longest_streak_card(watch_events: List[Dict]) -> Dict:
    """Generate longest streak card data."""
    # Get unique dates
    dates = set()
    for e in watch_events:
        ts = e.get("timestamp_local") or e.get("timestamp_utc")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                dates.add(dt.date())
            except:
                pass
    
    if not dates:
        return {"days": 0, "dates": ""}
    
    sorted_dates = sorted(dates)
    
    # Find longest consecutive streak
    max_streak = 1
    current_streak = 1
    streak_start = sorted_dates[0]
    max_streak_start = sorted_dates[0]
    max_streak_end = sorted_dates[0]
    
    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] - sorted_dates[i-1] == timedelta(days=1):
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
                max_streak_start = streak_start
                max_streak_end = sorted_dates[i]
        else:
            current_streak = 1
            streak_start = sorted_dates[i]
    
    dates_str = f"{max_streak_start.strftime('%b %d')} - {max_streak_end.strftime('%b %d')}"
    
    return {
        "days": max_streak,
        "dates": dates_str
    }


# ============================================
# PERSONALITY CARD (HARDCODED)
# ============================================

def generate_personality_card() -> Dict:
    """Generate personality card data (hardcoded for now)."""
    return {
        "type": "Curious Mind",
        "description": "You dive deep into diverse topics"
    }


# ============================================
# BINGE SESSIONS CARD
# ============================================

def generate_binge_sessions_card(watch_events: List[Dict], 
                                  binge_threshold_hours: float = 2.0) -> Dict:
    """Generate binge sessions card data."""
    # Compute sessions with duration
    sessions = compute_sessions_with_details(watch_events)
    
    # Filter binges (sessions > threshold)
    threshold_minutes = binge_threshold_hours * 60
    binges = [s for s in sessions if s["duration_minutes"] >= threshold_minutes]
    
    if not binges:
        return {
            "count": 0,
            "longest_duration": "0h 0m",
            "longest_date": ""
        }
    
    # Find longest
    longest = max(binges, key=lambda x: x["duration_minutes"])
    duration_hours = int(longest["duration_minutes"] // 60)
    duration_mins = int(longest["duration_minutes"] % 60)
    
    return {
        "count": len(binges),
        "longest_duration": f"{duration_hours}h {duration_mins}m",
        "longest_date": longest["start"].strftime("%B %d") if longest.get("start") else ""
    }


def compute_sessions_with_details(watch_events: List[Dict], 
                                   break_threshold_minutes: int = 60) -> List[Dict]:
    """Compute sessions with start time and duration."""
    timed_events = []
    for e in watch_events:
        ts = e.get("timestamp_local") or e.get("timestamp_utc")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                timed_events.append({"dt": dt, "event": e})
            except:
                pass
    
    if not timed_events:
        return []
    
    timed_events.sort(key=lambda x: x["dt"])
    
    sessions = []
    break_threshold = timedelta(minutes=break_threshold_minutes)
    
    session_start = timed_events[0]["dt"]
    session_end = timed_events[0]["dt"]
    event_count = 1
    
    for i in range(1, len(timed_events)):
        current = timed_events[i]["dt"]
        gap = current - timed_events[i-1]["dt"]
        
        if gap > break_threshold:
            duration = (session_end - session_start).total_seconds() / 60.0 + 5
            sessions.append({
                "start": session_start,
                "end": session_end,
                "duration_minutes": duration,
                "event_count": event_count
            })
            session_start = current
            session_end = current
            event_count = 1
        else:
            session_end = current
            event_count += 1
    
    # Last session
    duration = (session_end - session_start).total_seconds() / 60.0 + 5
    sessions.append({
        "start": session_start,
        "end": session_end,
        "duration_minutes": duration,
        "event_count": event_count
    })
    
    return sessions


# ============================================
# LATE NIGHT CARD
# ============================================

def generate_late_night_card(watch_events: List[Dict]) -> Dict:
    """Generate late night activity card data."""
    late_night_events = []
    
    for e in watch_events:
        hour = e.get("hour_local")
        if hour is not None and (hour >= 0 and hour < 5):  # 12 AM - 5 AM
            ts = e.get("timestamp_local") or e.get("timestamp_utc")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    late_night_events.append({"dt": dt, "event": e, "hour": hour})
                except:
                    pass
    
    if not late_night_events:
        return {
            "videos": 0,
            "latest_time": "",
            "latest_date": ""
        }
    
    # Find latest (highest hour, or closest to 5 AM)
    latest = max(late_night_events, key=lambda x: (x["hour"], x["dt"]))
    
    return {
        "videos": len(late_night_events),
        "latest_time": latest["dt"].strftime("%I:%M %p").lstrip("0") if latest else "",
        "latest_date": latest["dt"].strftime("%B %d") if latest else ""
    }


# ============================================
# HABITS CARD
# ============================================

def generate_habits_card(watch_events: List[Dict]) -> Dict:
    """
    Generate habits card data.
    
    Habit criteria:
    1. Channel must have >= 4 watches
    2. Watches must span at least 7 days (not all in one burst)
    3. Average gap between watches <= 14 days
    
    Ranking:
    - Primary: smaller avg gap = stronger habit
    - Secondary: more watches = stronger habit
    """
    # Group events by channel with timestamps
    channel_watches = defaultdict(list)
    
    for e in watch_events:
        channel = e.get("channel_clean")
        ts = e.get("timestamp_local") or e.get("timestamp_utc")
        if channel and ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                channel_watches[channel].append(dt)
            except:
                pass
    
    # Calculate watch frequency for each channel
    habits = []
    for channel, timestamps in channel_watches.items():
        if len(timestamps) >= 4:  # Need at least 4 watches to be a habit
            timestamps.sort()
            
            # Calculate total timespan
            timespan_days = (timestamps[-1] - timestamps[0]).days
            
            # Must span at least 7 days (not a one-day binge)
            if timespan_days < 7:
                continue
            
            # Calculate average gap
            gaps = [(timestamps[i+1] - timestamps[i]).days 
                    for i in range(len(timestamps)-1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            
            # Must be watched at least every 2 weeks on average
            if avg_gap <= 14:
                # Score combines consistency and frequency
                # Lower avg_gap + higher watch count = better score
                habit_score = avg_gap - (len(timestamps) * 0.1)  # Slight boost for more watches
                
                habits.append({
                    "channel": channel,
                    "frequency": f"{avg_gap:.1f} days",
                    "watch_count": len(timestamps),
                    "avg_gap_days": avg_gap,
                    "timespan_days": timespan_days,
                    "habit_score": habit_score
                })
    
    # Sort by habit score (lower = stronger habit)
    habits.sort(key=lambda x: x["habit_score"])
    
    if not habits:
        return {
            "total_channels": 0,
            "strongest": {"channel": "", "frequency": ""},
            "top_habits": []
        }
    
    return {
        "total_channels": len(habits),
        "strongest": {
            "channel": habits[0]["channel"],
            "frequency": habits[0]["frequency"]
        },
        "top_habits": habits[:5]
    }


# ============================================
# REWATCHED CARD
# ============================================

def generate_rewatched_card(watch_events: List[Dict]) -> Dict:
    """Generate rewatched videos card data."""
    video_counts = Counter()
    video_titles = {}
    
    for e in watch_events:
        title = e.get("title_original") or e.get("text_clean")
        if title:
            video_counts[title] += 1
            video_titles[title] = title
    
    # Filter to rewatched only (count > 1)
    rewatched = {title: count for title, count in video_counts.items() if count > 1}
    
    if not rewatched:
        return {
            "count": 0,
            "top_video": "",
            "top_times": 0
        }
    
    top_video = max(rewatched.items(), key=lambda x: x[1])
    
    return {
        "count": len(rewatched),
        "top_video": top_video[0][:100],  # Truncate long titles
        "top_times": top_video[1]
    }


# ============================================
# SUBSCRIPTIONS CARD
# ============================================

def generate_subscriptions_card(watch_events: List[Dict], 
                                 subscribe_events: List[Dict]) -> Dict:
    """Generate subscriptions card data."""
    # Get subscribed channels
    subscribed = set()
    for e in subscribe_events:
        channel = e.get("channel_clean") or e.get("text_clean")
        if channel:
            subscribed.add(channel)
    
    # Get watched channels
    watched = set(e.get("channel_clean") for e in watch_events if e.get("channel_clean"))
    
    # Calculate overlap
    overlap = subscribed & watched
    
    total = len(subscribed)
    watched_count = len(overlap)
    ghost = total - watched_count
    percentage = round(watched_count / total * 100, 1) if total > 0 else 0
    
    return {
        "total": total,
        "watched": watched_count,
        "ghost": ghost,
        "overlap_percentage": percentage
    }


# ============================================
# SEARCHES CARD
# ============================================

def generate_searches_card(search_events: List[Dict]) -> Dict:
    """Generate searches card data."""
    if not search_events:
        return {
            "total": 0,
            "top_search": "",
            "top_searches": []
        }
    
    search_terms = Counter()
    for e in search_events:
        term = e.get("text_clean") or e.get("title_original")
        if term:
            search_terms[term.lower()] += 1
    
    if not search_terms:
        return {
            "total": 0,
            "top_search": "",
            "top_searches": []
        }
    
    top_searches = [{"term": term, "count": count} 
                    for term, count in search_terms.most_common(5)]
    
    return {
        "total": len(search_events),
        "top_search": top_searches[0]["term"] if top_searches else "",
        "top_searches": top_searches
    }


# ============================================
# FIRST & LAST VIDEO CARD
# ============================================

def generate_first_last_card(watch_events: List[Dict]) -> Dict:
    """Generate first and last video card data."""
    timed_events = []
    
    for e in watch_events:
        ts = e.get("timestamp_local") or e.get("timestamp_utc")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                timed_events.append({"dt": dt, "event": e})
            except:
                pass
    
    if not timed_events:
        return {
            "first_video": {"title": "", "date": ""},
            "last_video": {"title": "", "date": ""}
        }
    
    timed_events.sort(key=lambda x: x["dt"])
    
    first = timed_events[0]
    last = timed_events[-1]
    
    def get_title(event):
        return (event.get("title_original") or 
                event.get("text_clean") or "Unknown")[:80]
    
    return {
        "first_video": {
            "title": get_title(first["event"]),
            "date": first["dt"].strftime("%B %d, %Y")
        },
        "last_video": {
            "title": get_title(last["event"]),
            "date": last["dt"].strftime("%B %d, %Y")
        }
    }


# ============================================
# PATTERNS CARD (Association Rule Mining)
# ============================================

def generate_patterns_card(watch_events: List[Dict]) -> Dict:
    """
    Discover viewing patterns using lightweight association rule mining.
    
    Focus on TOP CHANNELS ONLY to avoid noise from rarely-watched channels.
    
    Patterns detected:
    1. Channel + Day of week (e.g., "You watch X every Sunday")
    2. Channel + Time of day (e.g., "You watch X in the mornings")
    3. Weekend preference (e.g., "X is your weekend channel")
    """
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    time_slots = {
        "morning": (5, 12),    # 5 AM - 12 PM
        "afternoon": (12, 17), # 12 PM - 5 PM
        "evening": (17, 21),   # 5 PM - 9 PM
        "night": (21, 24),     # 9 PM - 12 AM
        "late night": (0, 5),  # 12 AM - 5 AM
    }
    
    # First, identify TOP CHANNELS (top 20 by watch count)
    channel_counts = Counter(
        e.get("channel_clean") for e in watch_events 
        if e.get("channel_clean")
    )
    
    if not channel_counts:
        return {"total_patterns": 0, "top_patterns": [], "insights": []}
    
    # Get top 20 channels (or fewer if user watched less)
    top_channels = set(ch for ch, _ in channel_counts.most_common(20))
    
    # Also require minimum 10 watches to be considered
    min_watches = max(10, len(watch_events) // 100)  # At least 1% of total or 10
    top_channels = {ch for ch in top_channels if channel_counts[ch] >= min_watches}
    
    if not top_channels:
        return {"total_patterns": 0, "top_patterns": [], "insights": []}
    
    patterns = []
    
    # 1. Channel + Day of Week associations (top channels only)
    channel_day_patterns = find_channel_day_patterns(watch_events, day_names, top_channels)
    patterns.extend(channel_day_patterns)
    
    # 2. Channel + Time Slot associations (top channels only)
    channel_time_patterns = find_channel_time_patterns(watch_events, time_slots, top_channels)
    patterns.extend(channel_time_patterns)
    
    # 3. Weekend vs Weekday preferences (top channels only)
    weekend_pattern = find_weekend_pattern(watch_events, top_channels)
    if weekend_pattern:
        patterns.append(weekend_pattern)
    
    # Sort by a combined score: confidence * watch_count (prioritize high-volume patterns)
    patterns.sort(key=lambda x: x.get("confidence", 0) * x.get("count", 1), reverse=True)
    
    # Take top 5 patterns
    top_patterns = patterns[:5]
    
    return {
        "total_patterns": len(patterns),
        "top_patterns": top_patterns,
        "insights": [p["insight"] for p in top_patterns]
    }


def find_channel_day_patterns(watch_events: List[Dict], day_names: List[str], top_channels: set) -> List[Dict]:
    """Find channels that are strongly associated with specific days (top channels only)."""
    # Count channel occurrences per day
    channel_day_counts = defaultdict(lambda: defaultdict(int))
    channel_total = defaultdict(int)
    day_total = defaultdict(int)
    
    for e in watch_events:
        channel = e.get("channel_clean")
        day = e.get("day_of_week")
        if channel and day is not None and channel in top_channels:
            channel_day_counts[channel][day] += 1
            channel_total[channel] += 1
            day_total[day] += 1
    
    total_events = sum(channel_total.values())
    
    patterns = []
    
    for channel, day_counts in channel_day_counts.items():
        for day, count in day_counts.items():
            # Calculate confidence: P(day | channel)
            confidence = count / channel_total[channel] if channel_total[channel] > 0 else 0
            
            # Calculate lift: how much more likely vs random
            expected = (channel_total[channel] * day_total[day]) / total_events if total_events > 0 else 0
            lift = count / expected if expected > 0 else 0
            
            # Strong pattern: confidence > 30% AND lift > 1.5 AND at least 5 occurrences
            if confidence >= 0.30 and lift >= 1.5 and count >= 5:
                day_name = day_names[day] if 0 <= day < 7 else "Unknown"
                patterns.append({
                    "type": "channel_day",
                    "channel": channel,
                    "day": day_name,
                    "confidence": confidence,
                    "lift": lift,
                    "count": count,
                    "insight": f"You watch **{channel}** on **{day_name}s** ({int(confidence*100)}% of the time)"
                })
    
    return patterns


def find_channel_time_patterns(watch_events: List[Dict], time_slots: Dict, top_channels: set) -> List[Dict]:
    """Find channels associated with specific time slots (top channels only)."""
    
    def get_time_slot(hour: int) -> Optional[str]:
        for slot_name, (start, end) in time_slots.items():
            if slot_name == "late night":
                if hour >= 0 and hour < 5:
                    return slot_name
            elif start <= hour < end:
                return slot_name
        return None
    
    # Count channel occurrences per time slot
    channel_slot_counts = defaultdict(lambda: defaultdict(int))
    channel_total = defaultdict(int)
    slot_total = defaultdict(int)
    
    for e in watch_events:
        channel = e.get("channel_clean")
        hour = e.get("hour_local")
        if channel and hour is not None and channel in top_channels:
            slot = get_time_slot(hour)
            if slot:
                channel_slot_counts[channel][slot] += 1
                channel_total[channel] += 1
                slot_total[slot] += 1
    
    total_events = sum(slot_total.values())
    
    patterns = []
    
    for channel, slot_counts in channel_slot_counts.items():
        for slot, count in slot_counts.items():
            confidence = count / channel_total[channel] if channel_total[channel] > 0 else 0
            expected = (channel_total[channel] * slot_total[slot]) / total_events if total_events > 0 else 0
            lift = count / expected if expected > 0 else 0
            
            # Strong pattern: confidence > 40% AND lift > 1.5 AND at least 5 occurrences
            if confidence >= 0.40 and lift >= 1.5 and count >= 5:
                time_phrase = {
                    "morning": "in the mornings",
                    "afternoon": "in the afternoons", 
                    "evening": "in the evenings",
                    "night": "at night",
                    "late night": "during late nights"
                }.get(slot, slot)
                
                patterns.append({
                    "type": "channel_time",
                    "channel": channel,
                    "time_slot": slot,
                    "confidence": confidence,
                    "lift": lift,
                    "count": count,
                    "insight": f"**{channel}** is your **{slot}** go-to ({int(confidence*100)}%)"
                })
    
    return patterns


def find_weekend_pattern(watch_events: List[Dict], top_channels: set) -> Optional[Dict]:
    """Find if watching behavior differs significantly on weekends (top channels only)."""
    weekday_channels = defaultdict(int)
    weekend_channels = defaultdict(int)
    
    for e in watch_events:
        channel = e.get("channel_clean")
        day = e.get("day_of_week")
        if channel and day is not None and channel in top_channels:
            if day in [5, 6]:  # Saturday, Sunday
                weekend_channels[channel] += 1
            else:
                weekday_channels[channel] += 1
    
    # Find channels that are predominantly weekend
    weekend_exclusive = []
    for channel, weekend_count in weekend_channels.items():
        weekday_count = weekday_channels.get(channel, 0)
        total = weekend_count + weekday_count
        if total >= 10:  # Need at least 10 total watches
            weekend_ratio = weekend_count / total
            if weekend_ratio >= 0.6:  # 60%+ on weekends
                weekend_exclusive.append((channel, weekend_ratio, total))
    
    if weekend_exclusive:
        top = max(weekend_exclusive, key=lambda x: x[2])  # Most watched
        return {
            "type": "weekend_preference",
            "channel": top[0],
            "confidence": top[1],
            "count": top[2],
            "insight": f"**{top[0]}** is your **weekend** channel ({int(top[1]*100)}% weekend views)"
        }
    
    return None

