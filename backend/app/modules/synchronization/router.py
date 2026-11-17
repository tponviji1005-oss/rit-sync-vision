"""
RIT Sync Vision - Offline Synchronization Router
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.database.session import get_db
from backend.app.modules.authentication.dependencies import get_current_user
from backend.app.modules.sessions.repository import session_repository
from backend.app.modules.synchronization.models import SyncEvent
from backend.app.modules.synchronization.repository import sync_repository
from backend.app.modules.synchronization.schemas import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncEventResponse,
)
from backend.app.modules.synchronization.service import sync_service
from backend.app.modules.users.models import User, UserRole

router = APIRouter(prefix="/sync", tags=["Offline Synchronization"])


@router.get("/status")
def get_sync_status():
    """Health and status endpoint for offline synchronization module."""
    return {"status": "ready", "module": "synchronization", "version": "1.0.0"}


@router.post("/attendance", response_model=SyncBatchResponse, status_code=status.HTTP_200_OK)
def sync_offline_attendance(
    batch: SyncBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
):
    """
    Synchronize a batch of offline attendance operations idempotently.

    - Requires authenticated Teacher or Administrator.
    - Idempotent: repeated submission with identical event_id returns DUPLICATE safely.
    - Replay protection: differing payloads for the same event_id surface as CONFLICT.
    - Conflict surfacing: teacher-finalized attendance records are never silently overwritten.
    - Partial batch resilience: invalid events receive REJECTED without failing valid events.
    """
    return sync_service.process_sync_batch(db, batch, current_user)


@router.get("/events/{event_id}", response_model=SyncEventResponse)
def get_sync_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
):
    """Retrieve details and audit information for a specific synchronization event."""
    event = sync_repository.get_by_event_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sync event '{event_id}' not found",
        )

    # Teacher access isolation: teacher can only inspect events for sessions they own
    role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_str == "teacher":
        session = session_repository.get_by_id(db, event.session_id)
        if session and session.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to inspect sync events for this session",
            )

    return event


@router.get("/sessions/{session_id}/events", response_model=List[SyncEventResponse])
def list_session_sync_events(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
):
    """List all synchronization events recorded for a capture session."""
    session = session_repository.get_by_session_id(db, session_id)
    if not session and session_id.isdigit():
        session = session_repository.get_by_id(db, int(session_id))

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_str == "teacher" and session.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access sync events for this session",
        )

    return sync_repository.list_by_session(db, session.id)
