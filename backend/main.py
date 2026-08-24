"""
IDO Backend - YouTube Takeout Processor
FastAPI application entry point
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.zip_routes import router as zip_router
from api.content_routes import router as content_router
from api.session_routes import router as session_router
from api.preprocess_routes import router as preprocess_router
from api.analytics_routes import router as analytics_router
from api.topic_routes import topic_router
from api.wrapped_routes import wrapped_router
# Google Data Portability ("Connect Google") flow -- SHELVED.
# The Data Portability API is country-restricted (unavailable for India-based accounts),
# so the feature is disabled while keeping the code intact. To re-enable, uncomment these
# two imports and the two include_router calls further down.
# from api.portability_routes import portability_router
# from api.account_routes import account_router

load_dotenv()

app = FastAPI(
    title="IDO",
    description="Process YouTube Takeout ZIP files and extract insights",
    version="1.0.0"
)

# CORS configuration for frontend.
# The OAuth/saved-Wrappeds flow sends an Authorization header, which makes it a
# credentialed request: browsers reject a wildcard origin once allow_credentials is on,
# so the allowed list is explicit. Keep it in sync with your frontend origin(s).
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(zip_router, prefix="/api/zip", tags=["ZIP Processing"])
app.include_router(content_router, prefix="/api/content", tags=["Content"])
app.include_router(session_router, prefix="/api/session", tags=["Session"])
app.include_router(preprocess_router, prefix="/api/preprocess", tags=["Preprocess"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(topic_router)
app.include_router(wrapped_router)
# app.include_router(portability_router)
# app.include_router(account_router)


@app.on_event("startup")
def _prepare_storage():
    """Create the wrapped table if it is missing.

    Storage is Supabase/Postgres only and requires DATABASE_URL -- there is no SQLite
    fallback, so local development and production behave identically.
    """
    from services import wrapped_store

    try:
        wrapped_store.init_schema()
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] Wrapped storage unavailable: {exc}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "IDO Backend"}


@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "zip": ["/api/zip/read", "/api/zip/extract"],
            "content": ["/api/content/preview"],
            "session": ["/api/session/store", "/api/session/{token}"],
            "preprocess": [
                "/api/preprocess/watch-history",
                "/api/preprocess/search-history", 
                "/api/preprocess/subscriptions",
                "/api/preprocess/all",
                "/api/preprocess/all-and-store"
            ]
        }
    }
