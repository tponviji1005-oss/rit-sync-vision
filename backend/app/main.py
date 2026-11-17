"""
RIT Sync Vision - Backend Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.modules.ai_processing.router import router as ai_router

app = FastAPI(
    title="RIT Sync Vision API",
    description="Vision-based Automated Attendance and Synchronization System",
    version="0.1.0",
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(ai_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "rit-sync-vision-backend"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
