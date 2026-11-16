"""
RIT Sync Vision - API v1 Router
"""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["Health"])
async def versioned_health_check():
    """
    Versioned health check endpoint for RIT-Sync Vision API v1.
    """
    return {
        "status": "ok",
        "service": "rit-sync-vision-backend",
        "version": "v1",
    }
