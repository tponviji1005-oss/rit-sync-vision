"""
RIT-Sync Vision - Shared System Constants
Defines cross-module contracts for attendance states, match states, reason codes, and session statuses.
"""

from enum import Enum


class MatchState(str, Enum):
    """AI Face Match Result States"""
    MATCHED = "MATCHED"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_QUALITY = "INSUFFICIENT_QUALITY"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class AttendanceCandidateState(str, Enum):
    """
    AI Attendance Candidate States (Proposals only; not final decisions).
    Core Principle: NOT_OBSERVED != ABSENT.
    """
    PRESENT_CANDIDATE = "PRESENT_CANDIDATE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_OBSERVED = "NOT_OBSERVED"


class FinalAttendanceStatus(str, Enum):
    """
    Final Teacher-Authorized Attendance Statuses.
    Only the teacher has the authority to assign PRESENT or ABSENT.
    """
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNRESOLVED = "UNRESOLVED"
    EXCUSED = "EXCUSED"


class ReasonCode(str, Enum):
    """Standard Reason Codes for AI Decisions & Quality Rejections"""
    # Quality-related
    FACE_TOO_SMALL = "FACE_TOO_SMALL"
    IMAGE_BLUR = "IMAGE_BLUR"
    POOR_LIGHTING = "POOR_LIGHTING"
    FACE_OCCLUDED = "FACE_OCCLUDED"
    FACE_ANGLE_UNSUITABLE = "FACE_ANGLE_UNSUITABLE"
    INSUFFICIENT_QUALITY = "INSUFFICIENT_QUALITY"

    # Recognition-related
    LOW_MATCH_CONFIDENCE = "LOW_MATCH_CONFIDENCE"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"  # Best vs second-best margin too narrow
    UNENROLLED_INDIVIDUAL = "UNENROLLED_INDIVIDUAL"

    # Evidence & Conflict
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # Too few frame observations
    CONFLICTING_IDENTITY = "CONFLICTING_IDENTITY"   # Track switched identities or multiple tracks matched same student
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"

    # Camera / Session
    CAMERA_DISCONNECTED = "CAMERA_DISCONNECTED"
    PERMIT_EXPIRED = "PERMIT_EXPIRED"
    MANUAL_FALLBACK_REQUESTED = "MANUAL_FALLBACK_REQUESTED"


class SessionState(str, Enum):
    """Capture Session State Model"""
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    CAPTURING = "CAPTURING"
    PROCESSING = "PROCESSING"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
