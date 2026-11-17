"""
RIT Sync Vision - Backend Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.v1.api import api_router

app = FastAPI(
    title="RIT Sync Vision API",
    description="Vision-based Automated Attendance and Synchronization System",
    version="0.1.0",
    debug=settings.DEBUG,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned API router (/api/v1)
app.include_router(api_router, prefix="/api/v1")


# Preserved root health check for backwards compatibility
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "rit-sync-vision-backend"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
    )
