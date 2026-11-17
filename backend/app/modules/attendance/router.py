"""
RIT Sync Vision - Attendance API Router
"""

from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, Header, HTTPException, status

from backend.app.core.security import decode_access_token
from backend.app.database.session import get_db
from backend.app.modules.attendance.ai_integration import check_ai_engine_status
from backend.app.modules.attendance.schemas import (
    AttendanceRecordResponse,
    AttendanceRecordUpdate,
    FinalizeAttendancePayload,
    ManualAttendanceCreate,
    ObservationSubmission,
    SessionAttendanceSummaryResponse,
)
from backend.app.modules.attendance.service import attendance_service
from backend.app.modules.authentication.dependencies import get_current_user
from backend.app.modules.users.models import User
from backend.app.modules.users.repository import user_repository

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])


def get_observation_caller(
    authorization: Optional[str] = Header(None),
    x_permit_token: Optional[str] = Header(None, alias="X-Permit-Token"),
    db=Depends(get_db),
) -> Tuple[Optional[User], Optional[str]]:
    """
    Extract observation caller identity: either an authenticated User (Teacher/Admin)
    or a capture permit token string.
    """
    permit_token = None
    if x_permit_token and x_permit_token.strip():
        permit_token = x_permit_token.strip()

    user = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            if payload.get("type") == "capture_permit" or str(payload.get("sub", "")).startswith("permit:"):
                if not permit_token:
                    permit_token = token
            else:
                username = payload.get("sub")
                if username:
                    user = user_repository.get_by_username(db, username=username)
        except Exception:
            if not permit_token:
                permit_token = token

    return user, permit_token


@router.post(
    "/sessions/{session_id}/proposals",
    response_model=List[AttendanceRecordResponse],
    summary="Submit AI Attendance Proposals",
    description="Record AI observation candidate proposals for teacher review. AI results never finalize attendance.",
)
@router.post(
    "/sessions/{session_id}/observations",
    response_model=List[AttendanceRecordResponse],
    summary="Submit AI Observations (Session path alias)",
    include_in_schema=False,
)
def submit_ai_proposals(
    session_id: str,
    payload: ObservationSubmission,
    auth: Tuple[Optional[User], Optional[str]] = Depends(get_observation_caller),
    db=Depends(get_db),
):
    """Submit AI observation proposals for an active classroom capture session."""
    user, permit_token = auth
    return attendance_service.submit_ai_proposals(
        db=db,
        session_identifier=session_id,
        payload=payload,
        current_user=user,
        permit_token=permit_token,
    )


@router.post(
    "/observations",
    response_model=List[AttendanceRecordResponse],
    summary="Submit AI Observations Ingestion",
    description="Ingest AI observations matching MANAGE.md §5 contract with session_id in payload.",
)
def ingest_ai_observations(
    payload: ObservationSubmission,
    auth: Tuple[Optional[User], Optional[str]] = Depends(get_observation_caller),
    db=Depends(get_db),
):
    """Ingest AI observations with session_id supplied in observation payload."""
    if not payload.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required in observation payload when invoking /attendance/observations",
        )
    user, permit_token = auth
    return attendance_service.submit_ai_proposals(
        db=db,
        session_identifier=payload.session_id,
        payload=payload,
        current_user=user,
        permit_token=permit_token,
    )


@router.get(
    "/ai-status",
    summary="Check AI Engine Integration Status",
    description="Inspect readiness and interface status of the ai_engine integration.",
)
def get_ai_status():
    """Retrieve integration contract and ai_engine module implementation state."""
    return check_ai_engine_status()


@router.get(
    "/sessions/{session_id}",
    response_model=SessionAttendanceSummaryResponse,
    summary="Get Session Attendance Review",
    description="Retrieve full session roster, candidate states, and summary. NOT_OBSERVED students are never automatically ABSENT.",
)
def get_session_attendance(
    session_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve complete attendance roster and verification status for a session."""
    return attendance_service.get_session_attendance(
        db=db,
        session_identifier=session_id,
        current_user=current_user,
    )


@router.post(
    "/sessions/{session_id}/finalize",
    response_model=List[AttendanceRecordResponse],
    summary="Finalize Session Attendance",
    description="Authorized teacher finalizes attendance decisions (PRESENT or ABSENT only).",
)
def finalize_attendance(
    session_id: str,
    payload: FinalizeAttendancePayload,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Teacher-authorized finalization of session attendance."""
    return attendance_service.finalize_attendance(
        db=db,
        session_identifier=session_id,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/sessions/{session_id}/manual",
    response_model=AttendanceRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Manual Attendance",
    description="Non-biometric manual attendance entry by an authorized teacher.",
)
def create_manual_record(
    session_id: str,
    manual_in: ManualAttendanceCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record manual attendance directly for a student without biometric AI input."""
    return attendance_service.create_manual_record(
        db=db,
        session_identifier=session_id,
        manual_in=manual_in,
        current_user=current_user,
    )


@router.get(
    "/records/{record_id}",
    response_model=AttendanceRecordResponse,
    summary="Get Attendance Record",
    description="Retrieve an individual attendance record by ID.",
)
def get_record(
    record_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a specific attendance record by identifier."""
    return attendance_service.get_record(
        db=db,
        record_id=record_id,
        current_user=current_user,
    )


@router.put(
    "/records/{record_id}",
    response_model=AttendanceRecordResponse,
    summary="Update Attendance Record",
    description="Teacher/admin override of an attendance record with mandatory audit explanation.",
)
def update_record(
    record_id: int,
    update_in: AttendanceRecordUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Modify an existing attendance record, logging previous status and audit notes."""
    return attendance_service.update_record(
        db=db,
        record_id=record_id,
        update_in=update_in,
        current_user=current_user,
    )


@router.get(
    "/students/{student_id}",
    response_model=List[AttendanceRecordResponse],
    summary="Get Student Attendance History",
    description="Retrieve all historical attendance records for a student across all sessions.",
)
def get_student_history(
    student_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full attendance history for a given student."""
    return attendance_service.get_student_history(
        db=db,
        student_identifier=student_id,
        current_user=current_user,
    )
