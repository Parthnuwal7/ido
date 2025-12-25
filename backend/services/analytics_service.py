"""
Analytics Service
Computes insights from preprocessed session data
"""

from collections import Counter
from typing import Optional
import json
from pathlib import Path


def load_session_events(token: str) -> tuple[list[dict], dict]:
    """Load events and stats from a preprocessed session."""
    storage_dir = Path(__file__).parent.parent / "storage"
    session_path = storage_dir / f"preprocessed_{token}.json"
    
    if not session_path.exists():
        return [], {}
    
    with open(session_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("events", []), data.get("stats", {})


def get_session_summary(token: str) -> dict:
    """
    Get overall session summary.
    
    Returns:
        - total_events, total_watch, total_search, total_subscribe
        - unique_channels
        - date_range (first and last timestamp)
        - language_breakdown
    """
    events, stats = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    # Get unique channels from watch events
    watch_events = [e for e in events if e.get("type") == "watch"]
    channels = set(e.get("channel_clean") for e in watch_events if e.get("channel_clean"))
    
    # Get date range
    timestamps = [e.get("timestamp_utc") for e in events if e.get("timestamp_utc")]
    timestamps.sort()
    
    return {
        "total_events": stats.get("total_events", len(events)),
        "total_watch": stats.get("total_watch", len(watch_events)),
        "total_search": stats.get("total_search", 0),
        "total_subscribe": stats.get("total_subscribe", 0),
        "unique_channels": len(channels),
        "date_range": {
            "first": timestamps[0] if timestamps else None,
            "last": timestamps[-1] if timestamps else None
        },
        "language_breakdown": stats.get("language_breakdown", {})
    }


def get_channel_analytics(token: str, top_n: int = 20, engagement_filter: str = "all") -> dict:
    """
    Get channel analytics.
    
    Args:
        token: Session token
        top_n: Number of top channels to return
        engagement_filter: "all" | "watch" (active) | "view" (passive)
    
    Returns:
        - top_channels: List of (channel, count) tuples
        - total_unique_channels
        - channel_distribution: Percentage breakdown
    """
    events, _ = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    # Get all watch-type events
    all_watch_events = [e for e in events if e.get("type") == "watch"]
    
    # Filter by engagement if specified
    if engagement_filter == "watch":
        # Watch = active engagement
        filtered_events = [e for e in all_watch_events if e.get("engagement") == "active"]
    elif engagement_filter == "view":
        # View = passive engagement
        filtered_events = [e for e in all_watch_events if e.get("engagement") == "passive"]
    else:
        # All watch events
        filtered_events = all_watch_events
    
    channel_counts = Counter(
        e.get("channel_clean") for e in filtered_events 
        if e.get("channel_clean")
    )
    
    # Get original channel names for display
    channel_display_names = {}
    for e in all_watch_events:
        clean = e.get("channel_clean")
        original = e.get("channel")
        if clean and original and clean not in channel_display_names:
            channel_display_names[clean] = original
    
    total_count = sum(channel_counts.values())
    top_channels = channel_counts.most_common(top_n)
    
    # Build result with display names and percentages
    top_channels_result = []
    for channel_clean, count in top_channels:
        display_name = channel_display_names.get(channel_clean, channel_clean)
        percentage = round((count / total_count) * 100, 2) if total_count > 0 else 0
        top_channels_result.append({
            "channel": display_name,
            "channel_clean": channel_clean,
            "count": count,
            "percentage": percentage
        })
    
    # Build view count distribution histogram
    # Buckets: 1, 2-5, 6-10, 11-20, 21-50, 51-100, 100+
    view_buckets = {
        "1": 0,
        "2-5": 0,
        "6-10": 0,
        "11-20": 0,
        "21-50": 0,
        "51-100": 0,
        "100+": 0
    }
    
    for count in channel_counts.values():
        if count == 1:
            view_buckets["1"] += 1
        elif count <= 5:
            view_buckets["2-5"] += 1
        elif count <= 10:
            view_buckets["6-10"] += 1
        elif count <= 20:
            view_buckets["11-20"] += 1
        elif count <= 50:
            view_buckets["21-50"] += 1
        elif count <= 100:
            view_buckets["51-100"] += 1
        else:
            view_buckets["100+"] += 1
    
    # Convert to list format for frontend
    view_distribution = [
        {"bucket": bucket, "count": count}
        for bucket, count in view_buckets.items()
    ]
    
    # Also compute summary stats for both types
    active_count = len([e for e in all_watch_events if e.get("engagement") == "active"])
    passive_count = len([e for e in all_watch_events if e.get("engagement") == "passive"])
    
    return {
        "total_unique_channels": len(channel_counts),
        "total_count": total_count,
        "engagement_filter": engagement_filter,
        "top_channels": top_channels_result,
        "other_count": total_count - sum(c["count"] for c in top_channels_result),
        "view_distribution": view_distribution,
        "engagement_summary": {
            "total_watch": active_count,
            "total_view": passive_count,
            "total_all": len(all_watch_events)
        }
    }


def get_watch_patterns(token: str) -> dict:
    """
    Get watch time patterns.
    
    Returns:
        - hourly_distribution: Watches per hour (0-23)
        - daily_distribution: Watches per day of week (0-6)
        - peak_hour, peak_day
        - weekly_peak_days: For each week, which day had most watches
        - time_intervals: Grouped by time periods (morning, afternoon, etc.)
        - circular_activity: Average watches per hour for radial chart
    """
    events, _ = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    watch_events = [e for e in events if e.get("type") == "watch"]
    
    # Count by hour
    hourly = Counter(e.get("hour_local") for e in watch_events if e.get("hour_local") is not None)
    
    # Count by day of week
    daily = Counter(e.get("day_of_week") for e in watch_events if e.get("day_of_week") is not None)
    
    # Build full distributions (fill missing with 0)
    hourly_dist = [{"hour": h, "count": hourly.get(h, 0)} for h in range(24)]
    daily_dist = [{"day": d, "count": daily.get(d, 0)} for d in range(7)]
    
    # Find peaks
    peak_hour = max(hourly_dist, key=lambda x: x["count"]) if hourly_dist else None
    peak_day = max(daily_dist, key=lambda x: x["count"]) if daily_dist else None
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # === Weekly Peak Day Analysis ===
    # Group events by week (using ISO week number) and find peak day for each week
    from datetime import datetime
    weekly_data = {}  # {(year, week): {day_of_week: count}}
    
    for e in watch_events:
        ts = e.get("timestamp_local")
        dow = e.get("day_of_week")
        if ts and dow is not None:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                year, week, _ = dt.isocalendar()
                key = (year, week)
                if key not in weekly_data:
                    weekly_data[key] = Counter()
                weekly_data[key][dow] += 1
            except:
                pass
    
    # Find peak day for each week
    weekly_peak_days = []
    peak_day_counter = Counter()  # Count how many weeks each day "wins"
    
    for (year, week), day_counts in sorted(weekly_data.items()):
        if day_counts:
            peak_dow = max(day_counts.keys(), key=lambda d: day_counts[d])
            peak_count = day_counts[peak_dow]
            weekly_peak_days.append({
                "year": year,
                "week": week,
                "peak_day": day_names[peak_dow],
                "peak_day_num": peak_dow,
                "count": peak_count
            })
            peak_day_counter[peak_dow] += 1
    
    # Overall winner: which day wins the most weeks
    overall_peak_day = None
    overall_peak_wins = 0
    if peak_day_counter:
        winner_dow = max(peak_day_counter.keys(), key=lambda d: peak_day_counter[d])
        overall_peak_day = day_names[winner_dow]
        overall_peak_wins = peak_day_counter[winner_dow]
    
    # === Time Intervals ===
    # Group hours into intervals
    intervals = {
        "Night (12AM-6AM)": range(0, 6),
        "Morning (6AM-12PM)": range(6, 12),
        "Afternoon (12PM-6PM)": range(12, 18),
        "Evening (6PM-12AM)": range(18, 24)
    }
    
    interval_counts = {}
    for name, hour_range in intervals.items():
        count = sum(hourly.get(h, 0) for h in hour_range)
        interval_counts[name] = count
    
    time_intervals = [
        {"interval": name, "count": count, "hours": f"{list(hours)[0]}-{list(hours)[-1]+1}"}
        for name, hours in intervals.items()
        for count in [interval_counts[name]]
    ]
    
    peak_interval = max(time_intervals, key=lambda x: x["count"]) if time_intervals else None
    
    # === Circular Activity (Average per hour) ===
    # Calculate average watches per hour across all days in the dataset
    total_days = len(weekly_data) * 7 if weekly_data else 1  # Approximate
    circular_activity = []
    total_watches = sum(hourly.values())
    
    for h in range(24):
        count = hourly.get(h, 0)
        # Percentage of total watches
        percentage = round((count / total_watches) * 100, 2) if total_watches > 0 else 0
        # Format hour label
        if h == 0:
            label = "12 AM"
        elif h < 12:
            label = f"{h} AM"
        elif h == 12:
            label = "12 PM"
        else:
            label = f"{h-12} PM"
        
        circular_activity.append({
            "hour": h,
            "label": label,
            "count": count,
            "percentage": percentage
        })
    
    return {
        "hourly_distribution": hourly_dist,
        "daily_distribution": daily_dist,
        "peak_hour": peak_hour["hour"] if peak_hour else None,
        "peak_hour_count": peak_hour["count"] if peak_hour else 0,
        "peak_day": day_names[peak_day["day"]] if peak_day and peak_day["day"] is not None else None,
        "peak_day_count": peak_day["count"] if peak_day else 0,
        # New fields
        "weekly_peak_days": weekly_peak_days[-12:],  # Last 12 weeks
        "overall_peak_day": overall_peak_day,
        "overall_peak_wins": overall_peak_wins,
        "total_weeks": len(weekly_data),
        "time_intervals": time_intervals,
        "peak_interval": peak_interval["interval"] if peak_interval else None,
        "circular_activity": circular_activity
    }


def get_temporal_trends(token: str) -> dict:
    """
    Analyze how watching patterns change month-to-month.
    
    Returns:
        - monthly_stats: Watch count, peak hour, peak day for each month
        - peak_hour_trend: How peak hour shifts over months
        - peak_day_trend: How peak day shifts over months
        - activity_trend: Total watches per month
    """
    events, _ = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    watch_events = [e for e in events if e.get("type") == "watch"]
    
    if not watch_events:
        return {
            "monthly_stats": [],
            "peak_hour_trend": [],
            "peak_day_trend": [],
            "activity_trend": [],
            "summary": "No watch events found"
        }
    
    from collections import defaultdict
    from datetime import datetime
    
    # Group by month
    monthly_data = defaultdict(lambda: {
        "watches": 0,
        "hourly": Counter(),
        "daily": Counter()
    })
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for event in watch_events:
        ts = event.get("timestamp_local") or event.get("timestamp_utc")
        hour = event.get("hour_local")
        dow = event.get("day_of_week")
        
        if not ts:
            continue
        
        try:
            # Parse year-month
            if "T" in ts:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(ts[:10], "%Y-%m-%d")
            
            month_key = f"{dt.year}-{dt.month:02d}"
            
            monthly_data[month_key]["watches"] += 1
            
            if hour is not None:
                monthly_data[month_key]["hourly"][hour] += 1
            
            if dow is not None:
                monthly_data[month_key]["daily"][dow] += 1
        except:
            continue
    
    # Build monthly stats
    monthly_stats = []
    peak_hour_trend = []
    peak_day_trend = []
    activity_trend = []
    
    for month_key in sorted(monthly_data.keys()):
        data = monthly_data[month_key]
        
        # Find peak hour
        peak_hour = None
        peak_hour_count = 0
        if data["hourly"]:
            peak_hour = max(data["hourly"].keys(), key=lambda h: data["hourly"][h])
            peak_hour_count = data["hourly"][peak_hour]
        
        # Find peak day
        peak_day = None
        peak_day_name = None
        peak_day_count = 0
        if data["daily"]:
            peak_day = max(data["daily"].keys(), key=lambda d: data["daily"][d])
            peak_day_name = day_names[peak_day]
            peak_day_count = data["daily"][peak_day]
        
        # Format peak hour label
        if peak_hour is not None:
            if peak_hour == 0:
                peak_hour_label = "12 AM"
            elif peak_hour < 12:
                peak_hour_label = f"{peak_hour} AM"
            elif peak_hour == 12:
                peak_hour_label = "12 PM"
            else:
                peak_hour_label = f"{peak_hour - 12} PM"
        else:
            peak_hour_label = "N/A"
        
        # Month name
        year, month = month_key.split("-")
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_label = f"{month_names[int(month)]} {year}"
        
        monthly_stats.append({
            "month": month_key,
            "month_label": month_label,
            "total_watches": data["watches"],
            "peak_hour": peak_hour,
            "peak_hour_label": peak_hour_label,
            "peak_hour_count": peak_hour_count,
            "peak_day": peak_day,
            "peak_day_name": peak_day_name,
            "peak_day_count": peak_day_count
        })
        
        # Trend data for charts
        peak_hour_trend.append({
            "month": month_key,
            "month_label": month_label,
            "peak_hour": peak_hour,
            "peak_hour_label": peak_hour_label
        })
        
        peak_day_trend.append({
            "month": month_key,
            "month_label": month_label,
            "peak_day": peak_day,
            "peak_day_name": peak_day_name
        })
        
        activity_trend.append({
            "month": month_key,
            "month_label": month_label,
            "watches": data["watches"]
        })
    
    # Detect significant shifts
    shifts = []
    for i in range(1, len(monthly_stats)):
        prev = monthly_stats[i-1]
        curr = monthly_stats[i]
        
        # Hour shift
        if prev["peak_hour"] is not None and curr["peak_hour"] is not None:
            hour_diff = abs(curr["peak_hour"] - prev["peak_hour"])
            if hour_diff >= 4:  # Significant if 4+ hours shift
                shifts.append({
                    "type": "peak_hour",
                    "from_month": prev["month_label"],
                    "to_month": curr["month_label"],
                    "from_value": prev["peak_hour_label"],
                    "to_value": curr["peak_hour_label"],
                    "description": f"Peak hour shifted from {prev['peak_hour_label']} to {curr['peak_hour_label']}"
                })
        
        # Day shift
        if prev["peak_day"] is not None and curr["peak_day"] is not None:
            if prev["peak_day"] != curr["peak_day"]:
                # Check if weekday<->weekend shift
                prev_weekend = prev["peak_day"] >= 5
                curr_weekend = curr["peak_day"] >= 5
                if prev_weekend != curr_weekend:
                    shifts.append({
                        "type": "peak_day",
                        "from_month": prev["month_label"],
                        "to_month": curr["month_label"],
                        "from_value": prev["peak_day_name"],
                        "to_value": curr["peak_day_name"],
                        "description": f"Shifted from {'weekend' if prev_weekend else 'weekday'} to {'weekend' if curr_weekend else 'weekday'}"
                    })
    
    # Generate summary
    if monthly_stats:
        first = monthly_stats[0]
        last = monthly_stats[-1]
        summary = f"Tracked {len(monthly_stats)} months from {first['month_label']} to {last['month_label']}"
        if shifts:
            summary += f" | {len(shifts)} significant pattern shifts detected"
    else:
        summary = "No monthly data available"
    
    return {
        "monthly_stats": monthly_stats,
        "peak_hour_trend": peak_hour_trend,
        "peak_day_trend": peak_day_trend,
        "activity_trend": activity_trend,
        "pattern_shifts": shifts[:10],  # Top 10 shifts
        "total_months": len(monthly_stats),
        "summary": summary
    }


def get_search_analytics(token: str, top_n: int = 20) -> dict:
    """
    Get search analytics.
    
    Returns:
        - total_searches
        - top_search_terms
        - language_breakdown for searches
    """
    events, _ = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    search_events = [e for e in events if e.get("type") == "search"]
    
    # Count search terms
    search_counts = Counter(
        e.get("text_clean") for e in search_events 
        if e.get("text_clean")
    )
    
    # Get raw terms for display
    term_display = {}
    for e in search_events:
        clean = e.get("text_clean")
        raw = e.get("text_raw")
        if clean and raw and clean not in term_display:
            term_display[clean] = raw
    
    top_searches = []
    for term_clean, count in search_counts.most_common(top_n):
        display = term_display.get(term_clean, term_clean)
        top_searches.append({
            "term": display,
            "term_clean": term_clean,
            "count": count
        })
    
    # Language breakdown for searches
    lang_counts = Counter(e.get("language_type") for e in search_events if e.get("language_type"))
    
    return {
        "total_searches": len(search_events),
        "unique_searches": len(search_counts),
        "top_searches": top_searches,
        "language_breakdown": dict(lang_counts)
    }


def get_subscription_overlap(token: str) -> dict:
    """
    Analyze overlap between subscriptions and watch history.
    
    Returns:
        - total_subscriptions
        - subscribed_and_watched: Channels you're subscribed to AND watched
        - watched_not_subscribed: Channels you watch but aren't subscribed to
        - subscribed_not_watched: Channels you're subscribed to but haven't watched
    """
    events, _ = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    # Get subscribed channels (lowercase)
    subscribe_events = [e for e in events if e.get("type") == "subscribe"]
    subscribed = set(e.get("channel_clean") for e in subscribe_events if e.get("channel_clean"))
    
    # Get watched channels (lowercase)
    watch_events = [e for e in events if e.get("type") == "watch"]
    watched = set(e.get("channel_clean") for e in watch_events if e.get("channel_clean"))
    
    # Calculate overlaps
    subscribed_and_watched = subscribed & watched
    watched_not_subscribed = watched - subscribed
    subscribed_not_watched = subscribed - watched
    
    # Get display names
    channel_display = {}
    for e in events:
        clean = e.get("channel_clean")
        original = e.get("channel")
        if clean and original:
            channel_display[clean] = original
    
    return {
        "total_subscriptions": len(subscribed),
        "total_watched_channels": len(watched),
        "subscribed_and_watched": {
            "count": len(subscribed_and_watched),
            "percentage": round(len(subscribed_and_watched) / len(subscribed) * 100, 1) if subscribed else 0,
            "channels": [channel_display.get(c, c) for c in list(subscribed_and_watched)[:20]]
        },
        "watched_not_subscribed": {
            "count": len(watched_not_subscribed),
            "channels": [channel_display.get(c, c) for c in list(watched_not_subscribed)[:20]]
        },
        "subscribed_not_watched": {
            "count": len(subscribed_not_watched),
            "channels": [channel_display.get(c, c) for c in list(subscribed_not_watched)[:20]]
        }
    }


def get_behavior_anomalies(token: str) -> dict:
    """
    Detect deviations from normal watching patterns.
    
    Identifies:
    - Late night sessions (watching after midnight when normally don't)
    - Binge periods (unusually high watch counts)
    - Off-peak hour activity
    - Weekly pattern changes
    """
    from datetime import datetime
    
    events, _ = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    watch_events = [e for e in events if e.get("type") == "watch"]
    
    if not watch_events:
        return {"anomalies": [], "late_night_sessions": [], "binge_days": []}
    
    # === Calculate baseline patterns ===
    # Average watches per hour across all data
    hourly_counts = Counter(e.get("hour_local") for e in watch_events if e.get("hour_local") is not None)
    total_watches = sum(hourly_counts.values())
    
    # Define "late night" as 12AM-5AM (hours 0-4)
    late_night_hours = {0, 1, 2, 3, 4}
    late_night_baseline = sum(hourly_counts.get(h, 0) for h in late_night_hours)
    late_night_percentage = (late_night_baseline / total_watches * 100) if total_watches > 0 else 0
    
    # === Group by date ===
    daily_data = {}  # {date_str: {hour: count, total: count}}
    
    for e in watch_events:
        ts = e.get("timestamp_local")
        hour = e.get("hour_local")
        if ts and hour is not None:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                date_str = dt.strftime("%Y-%m-%d")
                if date_str not in daily_data:
                    daily_data[date_str] = {"hours": Counter(), "total": 0}
                daily_data[date_str]["hours"][hour] += 1
                daily_data[date_str]["total"] += 1
            except:
                pass
    
    # Calculate average daily watches
    if daily_data:
        avg_daily_watches = sum(d["total"] for d in daily_data.values()) / len(daily_data)
        std_dev = (sum((d["total"] - avg_daily_watches) ** 2 for d in daily_data.values()) / len(daily_data)) ** 0.5
    else:
        avg_daily_watches = 0
        std_dev = 0
    
    # === Detect Late Night Sessions ===
    # Days where user watched significantly in late night hours (> usual)
    late_night_sessions = []
    
    for date_str, data in sorted(daily_data.items()):
        late_night_count = sum(data["hours"].get(h, 0) for h in late_night_hours)
        if late_night_count >= 3:  # At least 3 videos in late night
            late_night_sessions.append({
                "date": date_str,
                "late_night_count": late_night_count,
                "total_count": data["total"],
                "peak_hour": max(data["hours"].keys(), key=lambda h: data["hours"][h]) if data["hours"] else None
            })
    
    # === Detect Binge Days ===
    # Days with watch count > mean + 2*std_dev
    binge_threshold = avg_daily_watches + 2 * std_dev if std_dev > 0 else avg_daily_watches * 2
    binge_days = []
    
    for date_str, data in sorted(daily_data.items()):
        if data["total"] > binge_threshold and data["total"] >= 10:  # At least 10 videos
            binge_days.append({
                "date": date_str,
                "count": data["total"],
                "above_average_by": round(data["total"] - avg_daily_watches, 1),
                "multiplier": round(data["total"] / avg_daily_watches, 2) if avg_daily_watches > 0 else 0
            })
    
    # === Detect Weekly Pattern Shifts ===
    # Group by week and detect if hourly pattern changed significantly
    weekly_patterns = {}  # {(year, week): Counter of hours}
    
    for e in watch_events:
        ts = e.get("timestamp_local")
        hour = e.get("hour_local")
        if ts and hour is not None:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                year, week, _ = dt.isocalendar()
                key = (year, week)
                if key not in weekly_patterns:
                    weekly_patterns[key] = Counter()
                weekly_patterns[key][hour] += 1
            except:
                pass
    
    # Find weeks with unusual late-night activity
    unusual_weeks = []
    
    for (year, week), hour_counts in sorted(weekly_patterns.items()):
        week_total = sum(hour_counts.values())
        week_late_night = sum(hour_counts.get(h, 0) for h in late_night_hours)
        week_late_pct = (week_late_night / week_total * 100) if week_total > 0 else 0
        
        # If this week's late night % is significantly higher than baseline
        if week_late_pct > late_night_percentage * 1.5 and week_late_night >= 5:
            unusual_weeks.append({
                "year": year,
                "week": week,
                "late_night_count": week_late_night,
                "late_night_percentage": round(week_late_pct, 1),
                "baseline_percentage": round(late_night_percentage, 1),
                "total_watches": week_total
            })
    
    # === Detect Streaks (Consecutive Days) ===
    from datetime import timedelta
    
    def find_streaks(date_list, max_gap=1):
        """Find streaks of dates with at most max_gap days between them."""
        if not date_list:
            return []
        
        sorted_dates = sorted([datetime.strptime(d, "%Y-%m-%d") for d in date_list])
        streaks = []
        current_streak = [sorted_dates[0]]
        
        for i in range(1, len(sorted_dates)):
            gap = (sorted_dates[i] - sorted_dates[i-1]).days
            if gap <= max_gap + 1:  # Allow gap of max_gap days
                current_streak.append(sorted_dates[i])
            else:
                if len(current_streak) >= 2:
                    streaks.append(current_streak)
                current_streak = [sorted_dates[i]]
        
        if len(current_streak) >= 2:
            streaks.append(current_streak)
        
        return streaks
    
    # Find binge streaks (consecutive binge days, allowing 1 day gap)
    binge_dates = [d["date"] for d in binge_days]
    binge_streaks = find_streaks(binge_dates, max_gap=1)
    
    binge_watching_periods = []
    for streak in binge_streaks:
        start = streak[0].strftime("%Y-%m-%d")
        end = streak[-1].strftime("%Y-%m-%d")
        days = (streak[-1] - streak[0]).days + 1
        total_videos = sum(d["count"] for d in binge_days if d["date"] >= start and d["date"] <= end)
        binge_watching_periods.append({
            "start_date": start,
            "end_date": end,
            "duration_days": days,
            "total_videos": total_videos,
            "avg_per_day": round(total_videos / len(streak), 1)
        })
    
    # Find late night mood (consecutive late night sessions, allowing 1 day gap)
    late_night_dates = [s["date"] for s in late_night_sessions]
    late_night_streaks = find_streaks(late_night_dates, max_gap=1)
    
    late_night_moods = []
    for streak in late_night_streaks:
        start = streak[0].strftime("%Y-%m-%d")
        end = streak[-1].strftime("%Y-%m-%d")
        days = (streak[-1] - streak[0]).days + 1
        total_late = sum(s["late_night_count"] for s in late_night_sessions if s["date"] >= start and s["date"] <= end)
        late_night_moods.append({
            "start_date": start,
            "end_date": end,
            "duration_days": days,
            "total_late_videos": total_late
        })
    
    # === Additional Pattern Analysis ===
    
    # 1. Weekend Warrior Detection
    weekend_watches = 0
    weekday_watches = 0
    for e in watch_events:
        dow = e.get("day_of_week")
        if dow is not None:
            if dow >= 5:  # Saturday=5, Sunday=6
                weekend_watches += 1
            else:
                weekday_watches += 1
    
    total_dow = weekend_watches + weekday_watches
    weekend_pct = (weekend_watches / total_dow * 100) if total_dow > 0 else 0
    # If weekend (2 days) has > 35% of watches, that's weekend warrior territory
    is_weekend_warrior = weekend_pct > 35
    
    # 2. Night Owl vs Morning Person
    night_hours = {20, 21, 22, 23, 0, 1, 2, 3, 4}  # 8PM - 5AM
    morning_hours = {5, 6, 7, 8, 9, 10, 11}  # 5AM - 12PM
    
    night_count = sum(hourly_counts.get(h, 0) for h in night_hours)
    morning_count = sum(hourly_counts.get(h, 0) for h in morning_hours)
    
    if night_count > morning_count * 1.5:
        chronotype = "Night Owl"
    elif morning_count > night_count * 1.5:
        chronotype = "Early Bird"
    else:
        chronotype = "Balanced"
    
    # 3. Inactive Periods (gaps of 3+ days with no watching)
    sorted_dates = sorted(daily_data.keys())
    inactive_periods = []
    
    for i in range(1, len(sorted_dates)):
        prev = datetime.strptime(sorted_dates[i-1], "%Y-%m-%d")
        curr = datetime.strptime(sorted_dates[i], "%Y-%m-%d")
        gap = (curr - prev).days
        if gap >= 4:  # 3+ days gap
            inactive_periods.append({
                "start": sorted_dates[i-1],
                "end": sorted_dates[i],
                "gap_days": gap - 1
            })
    
    # === Build anomaly summary ===
    anomalies = []
    
    # Add binge watching periods
    for period in sorted(binge_watching_periods, key=lambda x: x["duration_days"], reverse=True)[:3]:
        anomalies.append({
            "type": "binge_streak",
            "date": f"{period['start_date']} to {period['end_date']}",
            "description": f"Binge watching period: {period['duration_days']} days, {period['total_videos']} videos",
            "severity": "high" if period["duration_days"] >= 5 else "medium"
        })
    
    # Add late night moods
    for mood in sorted(late_night_moods, key=lambda x: x["duration_days"], reverse=True)[:3]:
        anomalies.append({
            "type": "late_night_mood",
            "date": f"{mood['start_date']} to {mood['end_date']}",
            "description": f"Late night mood: {mood['duration_days']} consecutive nights",
            "severity": "high" if mood["duration_days"] >= 4 else "medium"
        })
    
    # Add top single-day anomalies
    for session in sorted(late_night_sessions, key=lambda x: x["late_night_count"], reverse=True)[:3]:
        anomalies.append({
            "type": "late_night",
            "date": session["date"],
            "description": f"Watched {session['late_night_count']} videos after midnight",
            "severity": "high" if session["late_night_count"] >= 10 else "medium"
        })
    
    for day in sorted(binge_days, key=lambda x: x["count"], reverse=True)[:3]:
        anomalies.append({
            "type": "binge",
            "date": day["date"],
            "description": f"Watched {day['count']} videos ({day['multiplier']}x above average)",
            "severity": "high" if day["multiplier"] >= 3 else "medium"
        })
    
    return {
        "baseline": {
            "avg_daily_watches": round(avg_daily_watches, 1),
            "std_dev": round(std_dev, 1),
            "late_night_baseline_pct": round(late_night_percentage, 1),
            "total_days": len(daily_data)
        },
        "anomalies": anomalies[:12],  # Top 12 anomalies
        "late_night_sessions": late_night_sessions[-20:],
        "binge_days": binge_days[-20:],
        "unusual_weeks": unusual_weeks[-10:],
        # New streak data
        "binge_watching_periods": binge_watching_periods,
        "late_night_moods": late_night_moods,
        # Behavior patterns
        "patterns": {
            "weekend_warrior": is_weekend_warrior,
            "weekend_pct": round(weekend_pct, 1),
            "chronotype": chronotype,
            "night_watches": night_count,
            "morning_watches": morning_count,
            "inactive_periods": inactive_periods[-5:]  # Last 5
        }
    }


def get_habit_formation(token: str, min_streak_days: int = 3) -> dict:
    """
    Detect habit formation patterns.
    
    Identifies:
    - Channels watched daily for consecutive days
    - Videos watched multiple times on different days
    - Content patterns that indicate habitual watching
    
    Args:
        token: Session token
        min_streak_days: Minimum consecutive days to count as a habit (default: 3)
    
    Returns:
        - channel_habits: Channels with daily watching streaks
        - video_habits: Videos watched on multiple days
        - content_habits: Topics/keywords watched daily
        - habit_strength: Overall habit formation score
    """
    events, _ = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    # Get watch events with dates
    watch_events = [e for e in events if e.get("type") == "watch"]
    
    if not watch_events:
        return {
            "channel_habits": [],
            "video_habits": [],
            "content_habits": [],
            "habit_strength": 0,
            "summary": "No watch events found"
        }
    
    # Group events by date and channel
    from collections import defaultdict
    from datetime import datetime, timedelta
    
    channel_by_date = defaultdict(set)  # date -> set of channels
    date_by_channel = defaultdict(set)  # channel -> set of dates
    
    # Track videos by date (using text_clean as identifier since we don't have video_id)
    date_by_video = defaultdict(set)  # video title -> set of dates
    video_info = {}  # video title -> {channel, first_seen, total_watches}
    
    # Also track micro_topics by date
    topic_by_date = defaultdict(set)  # date -> set of topics
    date_by_topic = defaultdict(set)  # topic -> set of dates
    
    for event in watch_events:
        ts = event.get("timestamp_local") or event.get("timestamp_utc")
        if not ts:
            continue
        
        # Extract date
        try:
            date_str = ts.split("T")[0] if "T" in ts else ts[:10]
        except:
            continue
        
        # Track channel
        channel = event.get("channel_clean")
        if channel:
            channel_by_date[date_str].add(channel)
            date_by_channel[channel].add(date_str)
        
        # Track video (using text_clean as identifier)
        video_title = event.get("text_clean") or event.get("text_raw")
        if video_title and len(video_title) > 5:  # Skip very short titles
            date_by_video[video_title].add(date_str)
            if video_title not in video_info:
                video_info[video_title] = {
                    "channel": channel or "Unknown",
                    "first_seen": date_str,
                    "total_watches": 0
                }
            video_info[video_title]["total_watches"] += 1
        
        # Track micro_topics if available
        topics = event.get("micro_topics", [])
        for topic in topics:
            topic_by_date[date_str].add(topic)
            date_by_topic[topic].add(date_str)
    
    # Find consecutive day streaks for each channel
    def find_daily_streaks(dates_set: set, min_days: int) -> list:
        """Find streaks of consecutive days."""
        if len(dates_set) < min_days:
            return []
        
        sorted_dates = sorted(dates_set)
        streaks = []
        current_streak = [sorted_dates[0]]
        
        for i in range(1, len(sorted_dates)):
            try:
                prev_date = datetime.strptime(sorted_dates[i-1], "%Y-%m-%d")
                curr_date = datetime.strptime(sorted_dates[i], "%Y-%m-%d")
                
                if (curr_date - prev_date).days == 1:
                    current_streak.append(sorted_dates[i])
                else:
                    if len(current_streak) >= min_days:
                        streaks.append({
                            "start": current_streak[0],
                            "end": current_streak[-1],
                            "days": len(current_streak)
                        })
                    current_streak = [sorted_dates[i]]
            except:
                current_streak = [sorted_dates[i]]
        
        # Don't forget the last streak
        if len(current_streak) >= min_days:
            streaks.append({
                "start": current_streak[0],
                "end": current_streak[-1],
                "days": len(current_streak)
            })
        
        return streaks
    
    # Find channel habits
    channel_habits = []
    for channel, dates in date_by_channel.items():
        streaks = find_daily_streaks(dates, min_streak_days)
        if streaks:
            # Calculate total days in habits
            total_habit_days = sum(s["days"] for s in streaks)
            longest_streak = max(s["days"] for s in streaks)
            
            channel_habits.append({
                "channel": channel,
                "total_days_watched": len(dates),
                "habit_streaks": streaks,
                "longest_streak": longest_streak,
                "total_habit_days": total_habit_days,
                "habit_score": min(100, total_habit_days * 10)  # Score 0-100
            })
    
    # Sort by longest streak, then total habit days
    channel_habits.sort(key=lambda x: (x["longest_streak"], x["total_habit_days"]), reverse=True)
    
    # Find video habits (videos watched on multiple different days)
    video_habits = []
    for video_title, dates in date_by_video.items():
        if len(dates) >= 2:  # Watched on at least 2 different days
            streaks = find_daily_streaks(dates, min_streak_days)
            info = video_info.get(video_title, {})
            
            video_habits.append({
                "title": video_title[:80] + "..." if len(video_title) > 80 else video_title,
                "channel": info.get("channel", "Unknown"),
                "days_watched": len(dates),
                "total_watches": info.get("total_watches", 0),
                "first_seen": info.get("first_seen", ""),
                "has_streak": len(streaks) > 0,
                "longest_streak": max((s["days"] for s in streaks), default=0)
            })
    
    # Sort video habits by days watched, then total watches
    video_habits.sort(key=lambda x: (x["days_watched"], x["total_watches"]), reverse=True)
    
    # Find content/topic habits (only for topics with >= 5 total occurrences)
    content_habits = []
    for topic, dates in date_by_topic.items():
        if len(dates) < 5:  # Skip rare topics
            continue
        
        streaks = find_daily_streaks(dates, min_streak_days)
        if streaks:
            total_habit_days = sum(s["days"] for s in streaks)
            longest_streak = max(s["days"] for s in streaks)
            
            content_habits.append({
                "topic": topic,
                "total_days": len(dates),
                "habit_streaks": streaks,
                "longest_streak": longest_streak,
                "total_habit_days": total_habit_days
            })
    
    # Sort content habits
    content_habits.sort(key=lambda x: (x["longest_streak"], x["total_habit_days"]), reverse=True)
    
    # Calculate overall habit strength
    total_channels_with_habits = len(channel_habits)
    max_channel_streak = max((h["longest_streak"] for h in channel_habits), default=0)
    
    # Habit strength: 0-100 score
    habit_strength = 0
    if total_channels_with_habits > 0:
        # Factors: number of habitual channels, longest streak, total habit days
        habit_strength = min(100, (
            total_channels_with_habits * 10 +
            max_channel_streak * 5 +
            sum(h["total_habit_days"] for h in channel_habits[:5])  # Top 5
        ))
    
    # Generate habit summary
    summary_parts = []
    if channel_habits:
        top_habit = channel_habits[0]
        summary_parts.append(
            f"Strongest habit: {top_habit['channel']} watched {top_habit['longest_streak']} days in a row"
        )
    if total_channels_with_habits > 1:
        summary_parts.append(f"{total_channels_with_habits} channels with daily habits")
    if video_habits:
        summary_parts.append(f"{len(video_habits)} rewatched videos")
    if content_habits:
        summary_parts.append(f"{len(content_habits)} recurring topics")
    
    return {
        "channel_habits": channel_habits,  # Return ALL channel habits
        "video_habits": video_habits[:30],  # Top 30 rewatched videos
        "content_habits": content_habits[:30],  # Top 30 topics
        "habit_strength": habit_strength,
        "total_channels_with_habits": total_channels_with_habits,
        "total_videos_rewatched": len(video_habits),
        "total_topics_with_habits": len(content_habits),
        "max_streak_days": max_channel_streak,
        "summary": " | ".join(summary_parts) if summary_parts else "No strong habits detected"
    }


def get_time_spent(token: str, break_threshold_minutes: int = 60, last_video_minutes: int = 5) -> dict:
    """
    Calculate approximate time spent on YouTube.
    
    Uses session detection: groups continuous watching periods separated by 
    significant breaks (>break_threshold_minutes).
    
    Args:
        token: Session token
        break_threshold_minutes: Gap that ends a session (default 60 min)
        last_video_minutes: Estimate for last video duration (default 5 min)
    
    Returns:
        - total_minutes, total_hours
        - average_daily_minutes
        - sessions stats (count, average, longest)
    """
    events, _ = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Get watch events with valid timestamps
    watch_events = []
    for e in events:
        if e.get("type") == "watch":
            ts = e.get("timestamp_local") or e.get("timestamp_utc")
            if ts:
                try:
                    if "T" in ts:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
                    watch_events.append({"timestamp": dt, "event": e})
                except:
                    pass
    
    if not watch_events:
        return {
            "total_minutes": 0,
            "total_hours": 0,
            "average_daily_minutes": 0,
            "total_days": 0,
            "sessions": {
                "total_count": 0,
                "average_duration_minutes": 0,
                "longest_session_minutes": 0
            },
            "summary": "No watch events with timestamps"
        }
    
    # Sort by timestamp
    watch_events.sort(key=lambda x: x["timestamp"])
    
    # Detect sessions
    sessions = []
    break_threshold = timedelta(minutes=break_threshold_minutes)
    
    session_start = watch_events[0]["timestamp"]
    session_end = watch_events[0]["timestamp"]
    session_event_count = 1
    
    for i in range(1, len(watch_events)):
        current = watch_events[i]["timestamp"]
        previous = watch_events[i-1]["timestamp"]
        gap = current - previous
        
        if gap > break_threshold:
            # End current session
            duration = (session_end - session_start).total_seconds() / 60.0
            duration += last_video_minutes  # Add estimate for last video
            sessions.append({
                "start": session_start,
                "end": session_end,
                "duration_minutes": duration,
                "event_count": session_event_count
            })
            # Start new session
            session_start = current
            session_end = current
            session_event_count = 1
        else:
            session_end = current
            session_event_count += 1
    
    # Don't forget the last session
    duration = (session_end - session_start).total_seconds() / 60.0
    duration += last_video_minutes
    sessions.append({
        "start": session_start,
        "end": session_end,
        "duration_minutes": duration,
        "event_count": session_event_count
    })
    
    # Calculate totals
    total_minutes = sum(s["duration_minutes"] for s in sessions)
    total_hours = round(total_minutes / 60, 1)
    
    # Get unique days
    unique_days = set()
    for we in watch_events:
        unique_days.add(we["timestamp"].date())
    total_days = len(unique_days)
    
    average_daily = round(total_minutes / total_days, 1) if total_days > 0 else 0
    
    # Session stats
    session_durations = [s["duration_minutes"] for s in sessions]
    avg_session = round(sum(session_durations) / len(session_durations), 1) if sessions else 0
    longest_session = round(max(session_durations), 1) if sessions else 0
    
    # Generate summary
    if total_hours >= 24:
        time_str = f"{int(total_hours // 24)} days {int(total_hours % 24)} hours"
    else:
        time_str = f"{total_hours} hours"
    
    summary = f"Spent approximately {time_str} on YouTube across {total_days} days ({len(sessions)} sessions)"
    
    return {
        "total_minutes": round(total_minutes, 1),
        "total_hours": total_hours,
        "average_daily_minutes": average_daily,
        "total_days": total_days,
        "sessions": {
            "total_count": len(sessions),
            "average_duration_minutes": avg_session,
            "longest_session_minutes": longest_session
        },
        "summary": summary
    }


def get_channel_distribution(token: str) -> dict:
    """
    Get channel distribution by view count bins.
    
    Returns:
    - bin_distribution: Channels grouped by view count [1, 2-5, 6-10, 11-20, 21-50, 51-100, 100+]
    - temporal_by_bin: Monthly breakdown of videos watched per bin
    """
    events, _ = load_session_events(token)
    
    if not events:
        return {"error": "Session not found or empty"}
    
    from collections import defaultdict
    from datetime import datetime
    
    # Get watch events
    watch_events = [e for e in events if e.get("type") == "watch"]
    
    # Count views per channel
    channel_counts = Counter(
        e.get("channel_clean") for e in watch_events 
        if e.get("channel_clean")
    )
    
    # Define bins
    bins = [
        (1, 1, "1"),
        (2, 5, "2-5"),
        (6, 10, "6-10"),
        (11, 20, "11-20"),
        (21, 50, "21-50"),
        (51, 100, "51-100"),
        (101, float('inf'), "100+")
    ]
    
    # Count channels per bin
    bin_distribution = []
    channel_bin_map = {}  # Map channel -> bin label
    
    for min_val, max_val, label in bins:
        channels_in_bin = [
            ch for ch, count in channel_counts.items() 
            if min_val <= count <= max_val
        ]
        video_count = sum(channel_counts[ch] for ch in channels_in_bin)
        
        bin_distribution.append({
            "bin": label,
            "channel_count": len(channels_in_bin),
            "video_count": video_count
        })
        
        for ch in channels_in_bin:
            channel_bin_map[ch] = label
    
    # Temporal breakdown by bin and month
    monthly_data = defaultdict(lambda: defaultdict(int))  # {month: {bin: count}}
    
    for event in watch_events:
        channel = event.get("channel_clean")
        ts = event.get("timestamp_local") or event.get("timestamp_utc")
        
        if not channel or not ts:
            continue
        
        bin_label = channel_bin_map.get(channel, "1")  # Default to "1"
        
        try:
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                continue
            month_key = f"{dt.year}-{dt.month:02d}"
            monthly_data[month_key][bin_label] += 1
        except:
            continue
    
    # Convert to sorted list
    temporal_by_bin = []
    for month in sorted(monthly_data.keys()):
        month_entry = {
            "month": month,
            "bins": {}
        }
        for min_val, max_val, label in bins:
            month_entry["bins"][label] = monthly_data[month].get(label, 0)
        temporal_by_bin.append(month_entry)
    
    # Summary stats
    total_channels = len(channel_counts)
    total_videos = sum(channel_counts.values())
    single_view_channels = sum(1 for count in channel_counts.values() if count == 1)
    
    return {
        "bin_distribution": bin_distribution,
        "temporal_by_bin": temporal_by_bin,
        "stats": {
            "total_channels": total_channels,
            "total_videos": total_videos,
            "single_view_channels": single_view_channels,
            "single_view_percentage": round(single_view_channels / total_channels * 100, 1) if total_channels > 0 else 0
        }
    }


def get_full_analytics(token: str) -> dict:
    """Get all analytics in one call."""
    return {
        "summary": get_session_summary(token),
        "channels": get_channel_analytics(token),
        "watch_patterns": get_watch_patterns(token),
        "searches": get_search_analytics(token),
        "subscription_overlap": get_subscription_overlap(token),
        "behavior_anomalies": get_behavior_anomalies(token),
        "habit_formation": get_habit_formation(token),
        "temporal_trends": get_temporal_trends(token),
        "time_spent": get_time_spent(token),
        "channel_distribution": get_channel_distribution(token)
    }
