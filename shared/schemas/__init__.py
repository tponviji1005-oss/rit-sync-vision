"""
RIT-Sync Vision - Shared Schemas
Defines Pydantic data contracts shared between AI Engine, Backend, and Frontend.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from shared.constants import (
    MatchState,
    AttendanceCandidateState,
    ReasonCode,
    SessionState,
)


class BoundingBox(BaseModel):
    """Bounding box coordinates for detected faces (normalized or absolute pixels)"""
    x: int = Field(..., description="Top-left X coordinate")
    y: int = Field(..., description="Top-left Y coordinate")
    width: int = Field(..., description="Width of bounding box")
    height: int = Field(..., description="Height of bounding box")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Detection confidence score")


class FaceQualityResult(BaseModel):
    """Quality evaluation metrics for a detected face"""
    is_usable: bool = Field(..., description="Whether observation meets threshold for recognition")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score 0-1")
    blur_score: float = Field(..., description="Laplacian variance or equivalent blur metric")
    brightness_score: float = Field(..., description="Mean luminance / exposure score")
    face_size_pixels: int = Field(..., description="Minimum face dimension in pixels (width or height)")
    reason_codes: List[ReasonCode] = Field(default_factory=list, description="Quality failure reasons")


class Observation(BaseModel):
    """Structured observation of a single face in one frame"""
    track_id: str = Field(..., description="Temporary multi-frame tracking ID (e.g. TRK_001)")
    candidate_student_id: Optional[str] = Field(None, description="Matched student ID if matched")
    match_state: MatchState = Field(..., description="MATCHED | UNKNOWN | INSUFFICIENT_QUALITY | NEEDS_REVIEW")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recognition confidence")
    reason_codes: List[ReasonCode] = Field(default_factory=list, description="Reason codes for decision")
    evidence_count: int = Field(
        default=0, ge=0, description="Number of usable frame observations (0 when no frame passed the quality gate)"
    )
    total_observations: int = Field(default=0, ge=0, description="Total frames in which this track was seen")
    bbox: Optional[BoundingBox] = None


class EnrolledTemplate(BaseModel):
    """Biometric feature template for an enrolled student"""
    student_id: str = Field(..., description="Unique student registration ID")
    student_name: str = Field(..., description="Student full name")
    embedding: List[float] = Field(..., description="Normalized feature vector")
    model_version: str = Field("v1.0", description="Model version used to create embedding")
    created_at: str = Field(..., description="ISO 8601 timestamp of enrollment")


class AttendanceCandidate(BaseModel):
    """
    AI attendance proposal for one student in a session.
    Provisional suggestion awaiting teacher review and finalization.
    """
    student_id: str = Field(..., description="Student identifier")
    student_name: str = Field(..., description="Student name")
    candidate_state: AttendanceCandidateState = Field(
        ..., description="PRESENT_CANDIDATE | NEEDS_REVIEW | NOT_OBSERVED"
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Overall aggregated confidence")
    reason_codes: List[ReasonCode] = Field(default_factory=list, description="Explanatory reason codes")
    evidence_count: int = Field(default=0, description="Total usable frames where student was observed")
    matched_track_id: Optional[str] = Field(None, description="Associated track ID if observed")


class SessionContext(BaseModel):
    """Context metadata passed into AI processing session"""
    session_id: str = Field(..., description="Unique capture session ID")
    class_id: str = Field(..., description="Class identifier (e.g. CSE-F)")
    subject_id: str = Field(..., description="Subject code (e.g. CS301)")
    teacher_id: str = Field(..., description="Authorized teacher user ID")
    permit_id: str = Field(..., description="Cryptographic capture permit ID")
    duration_seconds: int = Field(default=30, ge=30, le=120, description="Bounded capture window duration (30-120 s)")
    permit_expires_at: Optional[str] = Field(
        None, description="ISO 8601 expiry of the capture permit; capture is refused after this time"
    )


class AIProcessingResult(BaseModel):
    """Output contract from the AI Engine to the Backend"""
    session_id: str = Field(..., description="Session ID processed")
    total_frames_processed: int = Field(..., description="Count of frames read")
    total_tracks_detected: int = Field(..., description="Count of distinct face tracks")
    observations: List[Observation] = Field(default_factory=list, description="Per-track observations")
    candidates: List[AttendanceCandidate] = Field(
        default_factory=list, description="Final reconciled candidate list for class roster"
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    status: SessionState = Field(SessionState.COMPLETED, description="Status of the AI pipeline run")
    fault_reasons: List[ReasonCode] = Field(
        default_factory=list, description="Session-level faults (e.g. CAMERA_DISCONNECTED, PERMIT_EXPIRED)"
    )
    model_version: str = Field("unknown", description="Detector/encoder model identifiers used for this run")
    config: Dict[str, Any] = Field(default_factory=dict, description="Thresholds/config used, for traceability")


class DeviceHealthStatus(BaseModel):
    """Health check status of AI subsystem & peripherals"""
    camera_ready: bool
    model_ready: bool
    storage_ready: bool
    clock_synchronized: bool
    overall_status: str
    details: Dict[str, Any] = Field(default_factory=dict)
