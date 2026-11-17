"""
RIT Sync Vision - Attendance Data Models
"""

import enum
from datetime import datetime, timezone

try:
    from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
    from sqlalchemy.orm import relationship
    from backend.app.database.base import Base

    class AttendanceStatus(str, enum.Enum):
        """
        Attendance states defined in MANAGE.md §5:
        - PRESENT_CANDIDATE: sufficient system evidence; awaits teacher finalization.
        - NEEDS_REVIEW: uncertain evidence; requires explicit teacher decision.
        - NOT_OBSERVED: system did not obtain observation evidence (NEVER automatically ABSENT).
        - PRESENT: teacher-finalized present record.
        - ABSENT: teacher-authorized final decision (NEVER inferred from NOT_OBSERVED alone).
        """
        PRESENT_CANDIDATE = "PRESENT_CANDIDATE"
        NEEDS_REVIEW = "NEEDS_REVIEW"
        NOT_OBSERVED = "NOT_OBSERVED"
        PRESENT = "PRESENT"
        ABSENT = "ABSENT"

    class AttendanceRecord(Base):
        """
        SQLAlchemy model representing individual student attendance records per capture session.
        Enforces a unique constraint on (session_id, student_id) to prevent duplicate records.
        """
        __tablename__ = "attendance_records"
        __table_args__ = (
            UniqueConstraint("session_id", "student_id", name="uq_session_student_attendance"),
            Index("idx_attendance_session_student", "session_id", "student_id"),
        )

        id = Column(Integer, primary_key=True, index=True)
        session_id = Column(Integer, ForeignKey("capture_sessions.id"), nullable=False, index=True)
        session_code = Column(String(50), nullable=True, index=True)
        student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
        student_institutional_id = Column(String(50), nullable=False, index=True)
        status = Column(String(30), nullable=False, index=True)
        is_finalized = Column(Boolean, default=False, nullable=False, index=True)
        confidence = Column(Float, nullable=True)
        source = Column(String(50), default="AI_PROPOSAL", nullable=False)
        finalized_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
        finalized_at = Column(DateTime, nullable=True)
        previous_status = Column(String(30), nullable=True)
        notes = Column(Text, nullable=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        updated_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

        def __repr__(self):
            return (
                f"<AttendanceRecord id={self.id} session_id={self.session_id} "
                f"student='{self.student_institutional_id}' status='{self.status}' finalized={self.is_finalized}>"
            )

except Exception:
    class AttendanceStatus(str, enum.Enum):
        PRESENT_CANDIDATE = "PRESENT_CANDIDATE"
        NEEDS_REVIEW = "NEEDS_REVIEW"
        NOT_OBSERVED = "NOT_OBSERVED"
        PRESENT = "PRESENT"
        ABSENT = "ABSENT"

    class AttendanceRecord:
        """Fallback AttendanceRecord model matching the schema."""
        __tablename__ = "attendance_records"

        def __init__(
            self,
            id=None,
            session_id=None,
            session_code=None,
            student_id=None,
            student_institutional_id="",
            status=AttendanceStatus.PRESENT_CANDIDATE.value,
            is_finalized=False,
            confidence=None,
            source="AI_PROPOSAL",
            finalized_by_id=None,
            finalized_at=None,
            previous_status=None,
            notes=None,
            created_at=None,
            updated_at=None,
        ):
            self.id = id
            self.session_id = session_id
            self.session_code = session_code
            self.student_id = student_id
            self.student_institutional_id = student_institutional_id
            self.status = status if isinstance(status, str) else status.value
            self.is_finalized = is_finalized
            self.confidence = confidence
            self.source = source
            self.finalized_by_id = finalized_by_id
            self.finalized_at = finalized_at
            self.previous_status = previous_status
            self.notes = notes
            self.created_at = created_at or datetime.now(timezone.utc)
            self.updated_at = updated_at or datetime.now(timezone.utc)

        def __repr__(self):
            return (
                f"<AttendanceRecord id={self.id} session_id={self.session_id} "
                f"student='{self.student_institutional_id}' status='{self.status}' finalized={self.is_finalized}>"
            )
