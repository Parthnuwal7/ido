# Time-Based Insights Terminology

This document defines the terms and metrics used in the YouTube Wrapped time-based analytics.

---

## Baseline Metrics

| Term | Definition |
|------|------------|
| **Avg Daily Watches** | Average number of videos watched per day across the tracking period |
| **Std Deviation** | Measure of how much daily watch counts vary from the average |
| **Late Night Baseline %** | Percentage of all watches that occur between 12AM-5AM |
| **Total Days Tracked** | Number of unique days with at least one watch event |

---

## Anomaly Types

### Single-Day Anomalies

| Term | Trigger Condition | Severity |
|------|-------------------|----------|
| **Late Night Session** | ≥3 videos watched between 12AM-5AM | High if ≥10 videos, else Medium |
| **Binge Day** | Watch count > (mean + 2×std_dev) AND ≥10 videos | High if ≥3x average, else Medium |

### Streak-Based Patterns

| Term | Definition | Detection Logic |
|------|------------|-----------------|
| **Binge Watching Period** | Multiple consecutive binge days | Consecutive binge days with at most 1-day gap between them |
| **Late Night Mood** | Multiple consecutive late night sessions | Consecutive late night sessions with at most 1-day gap |

---

## Behavior Patterns

### Chronotype Classification

| Type | Condition | Hours Compared |
|------|-----------|----------------|
| **Night Owl** 🌙 | Night watches > 1.5× morning watches | Night: 8PM-5AM, Morning: 5AM-12PM |
| **Early Bird** ☀️ | Morning watches > 1.5× night watches | Night: 8PM-5AM, Morning: 5AM-12PM |
| **Balanced** ⏰ | Neither condition met | - |

### Weekend vs Weekday

| Pattern | Condition |
|---------|-----------|
| **Weekend Warrior** | >35% of total watches occur on weekends (Sat/Sun) |
| **Weekday Watcher** | ≤35% of total watches occur on weekends |

### Inactive Periods

| Term | Definition |
|------|------------|
| **Break/Inactive Period** | Gap of 4+ days between watch events (3+ consecutive days with no watching) |

---

## Time Intervals

| Interval | Hours |
|----------|-------|
| **Night** | 12AM - 6AM (0-5) |
| **Morning** | 6AM - 12PM (6-11) |
| **Afternoon** | 12PM - 6PM (12-17) |
| **Evening** | 6PM - 12AM (18-23) |

---

## Weekly Analysis

| Term | Definition |
|------|------------|
| **Weekly Peak Day** | The day of the week with the most watches for a given week |
| **Overall Peak Day** | The day that "wins" as peak day across the most weeks |
| **Peak Day Wins** | Number of weeks where a particular day had the highest watch count |

---

## Circular Activity Chart

The 24-hour clock visualization shows:
- **Bar Length**: Relative watch activity at each hour (normalized to max)
- **Color Intensity**: Higher intensity = more watches at that hour
- **Percentage**: What portion of total watches occurred at each hour

---

## Usage Notes

1. **Late Night Hours**: Defined as 12AM-5AM (hours 0-4) for anomaly detection
2. **Streak Gap Tolerance**: Up to 1 day gap allowed between events to still count as a streak
3. **Binge Threshold**: Dynamic, calculated as mean + 2×std_dev of daily watches
4. **Weekend Definition**: Saturday (day_of_week=5) and Sunday (day_of_week=6)
