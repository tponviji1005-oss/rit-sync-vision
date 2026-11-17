"""
RIT Sync Vision - Capture Session and Permit API Router
"""

from typing import List
from fastapi import APIRouter, Depends, status

from backend.app.database.session import get_db
from backend.app.modules.authentication.dependencies import get_current_user
from backend.app.modules.sessions.schemas import (
    PermitResponse,
    PermitValidateRequest,
    PermitValidateResponse,
    SessionCreate,
    SessionResponse,
)
from backend.app.modules.sessions.service import session_service
from backend.app.modules.users.models import User

router = APIRouter(prefix="/sessions", tags=["Capture Sessions & Permits"])


@router.post(
    "/",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Capture Session",
    description="Initialize an authorized classroom capture session and receive a time-bound permit (Teacher or Admin).",
)
def create_session(
    session_in: SessionCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start an authorized camera capture session and issue an active permit."""
    return session_service.create_session(db, session_in=session_in, current_user=current_user)


@router.get(
    "/",
    response_model=List[SessionResponse],
    summary="List Capture Sessions",
    description="List capture sessions (Teachers view their own sessions; Admins view all).",
)
def list_sessions(
    skip: int = 0,
    limit: int = 100,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List capture sessions accessible to the authenticated user."""
    return session_service.list_sessions(db, current_user=current_user, skip=skip, limit=limit)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get Capture Session",
    description="Retrieve details of a capture session by identifier string or ID.",
)
def get_session(
    session_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details and active permit state for a capture session."""
    return session_service.get_session(db, identifier=session_id, current_user=current_user)


@router.post(
    "/{session_id}/complete",
    response_model=SessionResponse,
    summary="Complete Capture Session",
    description="Mark a capture session COMPLETED and revoke its active permit (Teacher or Admin).",
)
def complete_session(
    session_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Finalize/stop capture session, revoking camera permit."""
    return session_service.complete_session(db, identifier=session_id, current_user=current_user)


@router.post(
    "/{session_id}/cancel",
    response_model=SessionResponse,
    summary="Cancel Capture Session",
    description="Abort/cancel a capture session and revoke its active permit (Teacher or Admin).",
)
def cancel_session(
    session_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel capture session, revoking camera permit."""
    return session_service.cancel_session(db, identifier=session_id, current_user=current_user)


@router.get(
    "/{session_id}/permit",
    response_model=PermitResponse,
    summary="Get Active Permit",
    description="Retrieve the active capture permit for an ongoing capture session.",
)
def get_permit(
    session_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the time-bound cryptographic permit for camera capture."""
    return session_service.get_permit(db, identifier=session_id, current_user=current_user)


@router.post(
    "/permit/validate",
    response_model=PermitValidateResponse,
    summary="Validate Capture Permit",
    description="Cryptographically and statefully validate a capture permit before camera ingestion or AI processing.",
)
def validate_permit(
    payload: PermitValidateRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify capture permit validity, expiration, and active session status. Requires authenticated user (SEC-SES-02)."""
    return session_service.validate_permit(db, permit_token=payload.permit_token)
