"""
RIT Sync Vision - API v1 Router
"""

from fastapi import APIRouter
from backend.app.modules.authentication.router import router as auth_router
from backend.app.modules.classrooms.router import router as classrooms_router
from backend.app.modules.sessions.router import router as sessions_router
from backend.app.modules.students.router import router as students_router
from backend.app.modules.subjects.router import router as subjects_router
from backend.app.modules.users.router import router as users_router

api_router = APIRouter()

# Mount authentication, student, classroom, subject, session, and user management routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(students_router)
api_router.include_router(classrooms_router)
api_router.include_router(subjects_router)
api_router.include_router(sessions_router)


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
