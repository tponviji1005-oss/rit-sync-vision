"""
RIT Sync Vision - Attendance Pydantic Schemas
"""

import enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.modules.attendance.models import AttendanceStatus


class MatchState(str, enum.Enum):
    """Supported AI observation match outcomes as defined in MANAGE.md §5."""
    MATCHED = "MATCHED"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_QUALITY = "INSUFFICIENT_QUALITY"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ObservationItem(BaseModel):
    """
    Individual AI observation item as defined in MANAGE.md §5 & §6.
    Represents recognition pipeline candidate output for teacher review.
    """
    track_id: str = Field(..., min_length=1, description="Temporary visual track ID")
    candidate_student_id: Optional[str] = Field(None, description="Candidate institutional student ID or null if unassigned")
    match_state: MatchState = Field(..., description="MATCHED | UNKNOWN | INSUFFICIENT_QUALITY | NEEDS_REVIEW")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Similarity or recognition confidence score")
    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable decision reasoning codes")
    evidence_count: int = Field(default=1, ge=0, description="Number of supporting observation frames")


class ObservationSubmission(BaseModel):
    """
    Payload for submitting AI observations to an active capture session.
    Proposes attendance candidates for teacher review. AI results never finalize attendance directly.
    Security: Permit tokens must be passed via secure header (X-Permit-Token), not in the request body.
    """
    session_id: Optional[str] = Field(None, description="Optional session ID if not provided in URL path")
    classroom_id: Optional[int] = Field(None, description="Optional classroom ID for cross-validation")
    observations: List[ObservationItem] = Field(..., min_length=1, description="List of observation items")


class FinalizeDecisionItem(BaseModel):
    """
    Individual student attendance decision by an authorized teacher.
    Only PRESENT and ABSENT are valid final statuses.
    """
    student_id: str = Field(..., min_length=1, description="Institutional student ID (e.g., RIT2026CS001)")
    status: str = Field(..., description="Finalized status: PRESENT or ABSENT")
    notes: Optional[str] = Field(None, max_length=500, description="Optional teacher remarks or justification")


class FinalizeAttendancePayload(BaseModel):
    """
    Batch attendance finalization payload submitted by an authorized teacher.
    """
    decisions: List[FinalizeDecisionItem] = Field(..., min_length=1, description="List of teacher finalization decisions")


class ManualAttendanceCreate(BaseModel):
    """
    Non-biometric manual attendance entry (e.g. roll call or manual override).
    Provides alternative to camera-based identification.
    """
    student_id: str = Field(..., min_length=1, description="Institutional student ID (e.g., RIT2026CS001)")
    status: str = Field(..., description="Attendance status: PRESENT or ABSENT")
    notes: Optional[str] = Field(None, max_length=500, description="Optional justification notes")


class AttendanceRecordUpdate(BaseModel):
    """
    Schema for teacher/admin modification of an existing attendance record.
    Requires audit notes explaining why the record was modified.
    """
    status: str = Field(..., description="Updated attendance status: PRESENT or ABSENT")
    notes: Optional[str] = Field(None, max_length=500, description="Mandatory audit note detailing reason for change")


class AttendanceRecordResponse(BaseModel):
    """
    Public representation of an individual student attendance record.
    Never exposes raw biometric data, embeddings, or camera imagery.
    """
    id: int
    session_id: int
    session_code: Optional[str] = None
    student_id: int
    student_institutional_id: str
    status: str
    is_finalized: bool
    confidence: Optional[float] = None
    source: str
    finalized_by_id: Optional[int] = None
    finalized_at: Optional[datetime] = None
    previous_status: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionAttendanceSummaryResponse(BaseModel):
    """
    Session attendance summary reflecting enrolled counts, candidate states, and finalized states.
    Students not observed are represented as NOT_OBSERVED and never automatically ABSENT.
    """
    session_id: int
    session_code: Optional[str] = None
    total_enrolled: int
    present_candidates: int
    needs_review: int
    not_observed: int
    finalized_present: int
    finalized_absent: int
    records: List[AttendanceRecordResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
