"""
RIT Sync Vision - Capture Session and Permit Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Schema for initializing an authorized classroom capture session."""
    classroom_id: int = Field(..., description="ID of the classroom where capture occurs")
    subject_id: int = Field(..., description="ID of the academic subject/course being conducted")
    teacher_id: Optional[int] = Field(None, description="Optional teacher ID; defaults to current authenticated teacher")
    camera_stream_url: Optional[str] = Field(None, max_length=255, description="Optional override for camera RTSP stream URL")
    duration_minutes: int = Field(default=60, ge=5, le=480, description="Session authorized duration in minutes")


class PermitResponse(BaseModel):
    """
    Representation of an authorized time-bound camera capture permit.
    SEC-SES-04: permit_token is populated only in explicit issuance/rotation endpoints
    and is omitted/null in general session metadata responses.
    """
    permit_id: str
    permit_token: Optional[str] = None
    classroom_id: int
    camera_stream_url: Optional[str] = None
    issued_at: datetime
    expires_at: datetime
    is_valid: bool

    model_config = {"from_attributes": True}


class PermitValidateRequest(BaseModel):
    """Request schema for validating camera capture permits before AI processing."""
    permit_token: str = Field(..., min_length=1, description="Signed permit token to validate")


class PermitValidateResponse(BaseModel):
    """Validation result for a capture permit."""
    valid: bool
    session_id: Optional[str] = None
    classroom_id: Optional[int] = None
    camera_stream_url: Optional[str] = None
    message: str


class SessionResponse(BaseModel):
    """
    Public representation of a capture session.
    CRITICAL: Does not contain biometric data or raw classroom footage.
    """
    id: int
    session_id: str
    classroom_id: int
    subject_id: int
    teacher_id: int
    status: str
    camera_stream_url: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    active_permit: Optional[PermitResponse] = None

    model_config = {"from_attributes": True}
