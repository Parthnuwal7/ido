---
title: IDO Backend
emoji: 📺
colorFrom: purple
colorTo: pink
sdk: docker
pinned: false
license: mit
---

# IDO Backend - YouTube Wrapped API

FastAPI backend for processing YouTube Takeout data and generating personalized Wrapped cards.

## Features

- 📊 Stateless ZIP processing (in-memory, no data stored)
- 🎯 19 insight cards with watch patterns
- 🔍 Association rule mining for viewing habits
- 🌐 Ready for ML model integration

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/wrapped/generate` | POST | Generate wrapped cards from ZIP |
| `/api/health` | GET | Health check |

## Usage

```bash
curl -X POST "https://your-space.hf.space/api/wrapped/generate" \
  -F "file=@takeout.zip" \
  -F "timezone=Asia/Kolkata"
```

## Tech Stack

- FastAPI
- spaCy (NLP)
- Python 3.11
