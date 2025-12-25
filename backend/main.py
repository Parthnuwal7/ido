"""
IDO Backend - YouTube Takeout Processor
FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.zip_routes import router as zip_router
from api.content_routes import router as content_router
from api.session_routes import router as session_router
from api.preprocess_routes import router as preprocess_router
from api.analytics_routes import router as analytics_router
from api.topic_routes import topic_router
from api.wrapped_routes import wrapped_router

app = FastAPI(
    title="IDO",
    description="Process YouTube Takeout ZIP files and extract insights",
    version="1.0.0"
)

# CORS configuration for frontend
# Allow all origins for production (HF Spaces + Vercel/Netlify frontend)
import os

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now; restrict in production if needed
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
