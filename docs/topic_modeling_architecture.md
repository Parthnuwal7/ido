# Topic Modeling & Channel Knowledge Base Architecture

## Overview

This document outlines the architecture for:
1. **Channel Knowledge Base** - Supabase storage for YouTube API channel metadata
2. **Topic Hierarchy** - Meso, Micro, and Macro topic assignment
3. **Caching Strategy** - Minimize API calls with smart batching

---

## 1. Channel Knowledge Base (Supabase)

### Data to Store

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `channel_id` | VARCHAR(24) | YouTube API | Primary key (UC...) |
| `channel_name` | TEXT | API | Display name |
| `description` | TEXT | API | Channel description |
| `created_at` | TIMESTAMP | API | Channel creation date |
| `country` | VARCHAR(5) | API | ISO country code |
| `subscriber_count` | BIGINT | API | Approximate count |
| `topic_ids` | TEXT[] | API | YouTube topic IDs |
| `topic_categories` | TEXT[] | API | Wikipedia URLs |
| `keywords` | TEXT[] | API | From brandingSettings |
| `fetched_at` | TIMESTAMP | System | When we fetched this |
| `fetch_count` | INT | System | How many times requested |

### Recommended Schema (Supabase Postgres)

```sql
CREATE TABLE channels (
    channel_id VARCHAR(24) PRIMARY KEY,
    channel_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP,
    country VARCHAR(5),
    subscriber_count BIGINT,
    topic_ids TEXT[],
    topic_categories TEXT[],
    keywords TEXT[],
    -- Metadata
    fetched_at TIMESTAMP DEFAULT NOW(),
    fetch_count INT DEFAULT 1,
    -- Derived fields (for faster queries)
    meso_topics TEXT[]  -- Mapped to our categories
);

-- Index for fast lookups
CREATE INDEX idx_channels_name ON channels (channel_name);
CREATE INDEX idx_channels_meso ON channels USING GIN (meso_topics);
```

### Why This Schema?

1. **Fast Lookup**: Primary key on `channel_id` for O(1) lookups
2. **Array Storage**: `TEXT[]` for topic lists - native Postgres, queryable with `ANY()`
3. **Age Tracking**: `fetched_at` lets us refresh stale data (>30 days old)
4. **Popularity Tracking**: `fetch_count` helps identify popular channels
5. **Pre-computed Meso**: Store derived meso topics to avoid re-mapping

---

## 2. Topic Hierarchy

### Level 1: Meso Topics (YouTube Categories)

**Source**: YouTube API `topicCategories` + our category mapping

```
┌─────────────────────────────────────────────────────┐
│                   MESO TOPICS                        │
│  (YouTube Categories - 32 predefined)               │
├─────────────────────────────────────────────────────┤
│ Entertainment, Music, Gaming, Education,           │
│ News & Politics, Science & Tech, Sports,           │
│ Comedy, Film & Animation, Travel, etc.             │
└─────────────────────────────────────────────────────┘
```

**Mapping Strategy**:
1. Map YouTube `topicCategories` URLs → Our category IDs
2. If channel has multiple topics, assign primary (first) + secondary
3. Fallback: Use `keywords` to infer category

### Level 2: Micro Topics (Extracted from Titles)

**Sources**:
- Video titles (`text_clean`)
- Channel keywords
- Hashtags in titles

**Extraction Methods**:
| Method | Example | Output |
|--------|---------|--------|
| NER | "Elon Musk launches..." | `[PERSON: Elon Musk]` |
| Nouns | "iPhone 15 review" | `[iPhone 15, review]` |
| Hashtags | "#shorts #gaming" | `[shorts, gaming]` |
| Keywords | Channel keywords | `[tech, unboxing]` |

**Processing Pipeline**:
```
text_clean → spaCy NER → Extract nouns → Normalize → Deduplicate
```

### Level 3: Macro Topics (Aggregated Themes)

**Strategy**: Combine Meso + Micro to identify user's overarching interests

```
┌──────────────────────────────────────────────────────────────┐
│                      MACRO TOPICS                             │
│              (User-level interest themes)                     │
├──────────────────────────────────────────────────────────────┤
│ Examples:                                                     │
│ • "Tech Enthusiast" = (Science & Tech + Apple + Reviews)     │
│ • "Music Lover" = (Music + Multiple artists + Concerts)      │
│ • "News Junkie" = (News + Politics + Current events)         │
│ • "Gamer" = (Gaming + Specific games + Esports)              │
└──────────────────────────────────────────────────────────────┘
```

**Assignment Logic** (to design later):
1. Weighted combination of Meso categories
2. Frequency of Micro topics
3. Rule-based classification or ML clustering

---

## 3. Processing Flow

### On User Upload

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHANNEL PROCESSING FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Parse watch events → Extract unique channel IDs             │
│                              ↓                                   │
│  2. Query Supabase: Which channels do we already have?          │
│       ├── HIT: Load from DB, skip API call                      │
│       └── MISS: Add to "unknown channels" list                  │
│                              ↓                                   │
│  3. Filter unknown: Keep only if watch_count > 1                │
│       (Single-watch channels = probably not worth API call)     │
│                              ↓                                   │
│  4. Batch API calls: YouTube Data API v3                        │
│       (50 channels per request, respect quotas)                 │
│                              ↓                                   │
│  5. Store results: Upsert into Supabase                         │
│                              ↓                                   │
│  6. Assign Meso topics: Map topicCategories → categories        │
│                              ↓                                   │
│  7. Return enriched data to client                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Batch File Strategy

Since we process multiple JSON files sequentially:

```python
# Pseudo-code
unknown_channels = set()
channel_watch_counts = Counter()

# Phase 1: Scan all files, collect unique channels
for json_file in user_files:
    for event in json_file:
        channel_id = extract_channel_id(event)
        channel_watch_counts[channel_id] += 1

# Phase 2: Query existing
known = supabase.query(channel_watch_counts.keys())
unknown = set(channel_watch_counts.keys()) - known

# Phase 3: Filter by importance
important_unknown = {ch for ch in unknown if channel_watch_counts[ch] > 1}

# Phase 4: Batch API calls
for batch in chunks(important_unknown, 50):
    results = youtube_api.channels(batch)
    supabase.upsert(results)
```

---

## 4. Potential Vulnerabilities & Mitigations

### API & Rate Limits

| Risk | Impact | Mitigation |
|------|--------|------------|
| YouTube API quota exceeded | Processing halted | Implement quotas tracking, defer non-critical calls |
| Supabase connection limits | Slow queries | Connection pooling, batch inserts |
| Large batch failures | Partial data | Transaction-based upserts, retry logic |

### Data Quality

| Risk | Impact | Mitigation |
|------|--------|------------|
| Stale channel data | Outdated topics | `fetched_at` check, refresh if >30 days |
| Missing topic categories | No meso topic | Fallback to keyword-based inference |
| Non-English content | NER fails | Language detection, skip NER for non-English |
| Deleted channels | API returns nothing | Mark as `deleted` in DB, don't retry |

### Edge Cases

| Case | Handling |
|------|----------|
| Channel watched 100+ times | Priority API call, cache aggressively |
| Channel watched once | Skip API call unless user explicitly requests |
| Private/deleted channel | Store as "unavailable", use cached name from watch history |
| Auto-generated music channels | Special handling (YouTube Music topics) |

### Security

| Risk | Mitigation |
|------|------------|
| API key exposure | Environment variables, server-side only |
| User IP/device tracking | Anonymize, hash IPs, GDPR compliance |
| Data retention | Define retention policy, allow deletion |

---

## 5. Supabase Table Design (Final)

```sql
-- Main channels table
CREATE TABLE channels (
    channel_id VARCHAR(24) PRIMARY KEY,
    channel_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP,
    country VARCHAR(5),
    subscriber_count BIGINT,
    topic_ids TEXT[],
    topic_categories TEXT[],
    keywords TEXT[],
    meso_topics TEXT[],  -- Pre-mapped categories
    -- Metadata
    fetched_at TIMESTAMP DEFAULT NOW(),
    fetch_count INT DEFAULT 1,
    is_available BOOLEAN DEFAULT TRUE
);

-- Traffic/analytics table (separate)
CREATE TABLE traffic_logs (
    id SERIAL PRIMARY KEY,
    session_id UUID,
    ip_hash VARCHAR(64),  -- Hashed IP for privacy
    user_agent TEXT,
    device_type VARCHAR(20),
    country VARCHAR(5),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 6. Questions for You

1. **API Quota**: Do you have a YouTube Data API key? What's your daily quota?
2. **Refresh Policy**: How often should we re-fetch channel data? (Suggestion: 30 days)
3. **Single-watch threshold**: Is >1 watch the right threshold for API calls?
4. **Meso fallback**: If no topic categories, use keywords or skip?
5. **Traffic tracking scope**: What specific metrics do you want to capture?

---

## Next Steps

1. [ ] Set up Supabase project and create tables
2. [ ] Implement channel lookup service
3. [ ] Create YouTube API integration (with quota tracking)
4. [ ] Build batch processing pipeline
5. [ ] Implement meso topic mapping
6. [ ] Add micro topic extraction (NER)
7. [ ] Design macro topic assignment logic
