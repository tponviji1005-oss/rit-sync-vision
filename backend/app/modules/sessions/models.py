"""
RIT Sync Vision - Capture Session and Permit Data Models
"""

import enum
from datetime import datetime, timezone
import uuid

try:
    from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, text
    from sqlalchemy.orm import relationship
    from backend.app.database.base import Base

    class SessionStatus(str, enum.Enum):
        ACTIVE = "ACTIVE"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"
        EXPIRED = "EXPIRED"

    class CaptureSession(Base):
        """
        SQLAlchemy model representing an authorized classroom capture session.
        Enforces a partial unique constraint: only one active session per classroom.
        """
        __tablename__ = "capture_sessions"
        __table_args__ = (
            Index(
                "uq_active_classroom_session",
                "classroom_id",
                unique=True,
                sqlite_where=text("status = 'ACTIVE'"),
            ),
        )

        id = Column(Integer, primary_key=True, index=True)
        session_id = Column(String(50), unique=True, index=True, nullable=False)
        classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False, index=True)
        subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
        teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
        status = Column(String(20), default=SessionStatus.ACTIVE.value, nullable=False, index=True)
        camera_stream_url = Column(String(255), nullable=True)
        start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        end_time = Column(DateTime, nullable=True)
        expires_at = Column(DateTime, nullable=False)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        updated_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

        def __repr__(self):
            return f"<CaptureSession id={self.id} session_id='{self.session_id}' status='{self.status}'>"

    class CapturePermit(Base):
        """
        SQLAlchemy model representing an authorized time-bound camera capture permit.
        SEC-SES-01: Stores only the SHA-256 token_hash at rest, never raw permit tokens.
        """
        __tablename__ = "capture_permits"

        id = Column(Integer, primary_key=True, index=True)
        permit_id = Column(String(50), unique=True, index=True, nullable=False)
        session_id = Column(Integer, ForeignKey("capture_sessions.id"), nullable=False, index=True)
        token_hash = Column(String(64), index=True, nullable=False)
        issued_to_id = Column(Integer, ForeignKey("users.id"), nullable=False)
        classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
        camera_stream_url = Column(String(255), nullable=True)
        issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        expires_at = Column(DateTime, nullable=False)
        is_revoked = Column(Boolean, default=False, nullable=False)

        def __repr__(self):
            return f"<CapturePermit id={self.id} permit_id='{self.permit_id}' revoked={self.is_revoked}>"

except Exception:
    class SessionStatus(str, enum.Enum):
        ACTIVE = "ACTIVE"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"
        EXPIRED = "EXPIRED"

    class CaptureSession:
        """Fallback CaptureSession model matching the schema."""
        __tablename__ = "capture_sessions"

        def __init__(
            self,
            id=None,
            session_id="",
            classroom_id=None,
            subject_id=None,
            teacher_id=None,
            status=SessionStatus.ACTIVE.value,
            camera_stream_url=None,
            start_time=None,
            end_time=None,
            expires_at=None,
            created_at=None,
            updated_at=None,
        ):
            self.id = id
            self.session_id = session_id or f"SES-{uuid.uuid4().hex[:8].upper()}"
            self.classroom_id = classroom_id
            self.subject_id = subject_id
            self.teacher_id = teacher_id
            self.status = status if isinstance(status, str) else status.value
            self.camera_stream_url = camera_stream_url
            self.start_time = start_time or datetime.now(timezone.utc)
            self.end_time = end_time
            self.expires_at = expires_at
            self.created_at = created_at or datetime.now(timezone.utc)
            self.updated_at = updated_at or datetime.now(timezone.utc)

        def __repr__(self):
            return f"<CaptureSession id={self.id} session_id='{self.session_id}' status='{self.status}'>"

    class CapturePermit:
        """Fallback CapturePermit model matching the schema with token_hash."""
        __tablename__ = "capture_permits"

        def __init__(
            self,
            id=None,
            permit_id="",
            session_id=None,
            token_hash="",
            issued_to_id=None,
            classroom_id=None,
            camera_stream_url=None,
            issued_at=None,
            expires_at=None,
            is_revoked=False,
        ):
            self.id = id
            self.permit_id = permit_id or f"PERMIT-{uuid.uuid4().hex[:8].upper()}"
            self.session_id = session_id
            self.token_hash = token_hash
            self.issued_to_id = issued_to_id
            self.classroom_id = classroom_id
            self.camera_stream_url = camera_stream_url
            self.issued_at = issued_at or datetime.now(timezone.utc)
            self.expires_at = expires_at
            self.is_revoked = is_revoked

        def __repr__(self):
            return f"<CapturePermit id={self.id} permit_id='{self.permit_id}' revoked={self.is_revoked}>"
