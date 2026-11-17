"""
RIT Sync Vision - Offline Synchronization Data Models
"""

import enum
from datetime import datetime, timezone

try:
    from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
    from backend.app.database.base import Base

    class SyncEventStatus(str, enum.Enum):
        """Synchronization processing states."""
        SYNCED = "SYNCED"
        DUPLICATE = "DUPLICATE"
        CONFLICT = "CONFLICT"
        REJECTED = "REJECTED"

    class SyncEvent(Base):
        """
        SQLAlchemy model representing an offline attendance event.
        Tracks unique event_id for idempotency and safe retry processing.
        """
        __tablename__ = "sync_events"
        __table_args__ = (
            UniqueConstraint("event_id", name="uq_sync_event_id"),
            Index("idx_sync_events_session", "session_id"),
            Index("idx_sync_events_student", "student_id"),
        )

        id = Column(Integer, primary_key=True, index=True)
        event_id = Column(String(100), unique=True, index=True, nullable=False)
        session_id = Column(Integer, ForeignKey("capture_sessions.id"), nullable=False, index=True)
        session_code = Column(String(50), nullable=True, index=True)
        student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
        student_institutional_id = Column(String(50), nullable=False, index=True)
        event_type = Column(String(50), default="RECORD_ATTENDANCE", nullable=False)
        status = Column(String(30), nullable=False)
        payload_hash = Column(String(64), nullable=False)
        sync_status = Column(String(30), nullable=False, index=True)
        attendance_record_id = Column(Integer, ForeignKey("attendance_records.id"), nullable=True)
        submitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
        client_timestamp = Column(DateTime, nullable=False)
        server_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        error_message = Column(Text, nullable=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        updated_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

        def __repr__(self):
            return (
                f"<SyncEvent id={self.id} event_id='{self.event_id}' "
                f"session='{self.session_code}' student='{self.student_institutional_id}' "
                f"status='{self.sync_status}'>"
            )

except Exception:
    class SyncEventStatus(str, enum.Enum):
        SYNCED = "SYNCED"
        DUPLICATE = "DUPLICATE"
        CONFLICT = "CONFLICT"
        REJECTED = "REJECTED"

    class SyncEvent:
        """Fallback SyncEvent model for isolated test / SQLite environments."""
        __tablename__ = "sync_events"

        def __init__(
            self,
            id=None,
            event_id="",
            session_id=None,
            session_code=None,
            student_id=None,
            student_institutional_id="",
            event_type="RECORD_ATTENDANCE",
            status="",
            payload_hash="",
            sync_status="SYNCED",
            attendance_record_id=None,
            submitted_by_id=None,
            client_timestamp=None,
            server_timestamp=None,
            error_message=None,
            created_at=None,
            updated_at=None,
        ):
            self.id = id
            self.event_id = event_id
            self.session_id = session_id
            self.session_code = session_code
            self.student_id = student_id
            self.student_institutional_id = student_institutional_id
            self.event_type = event_type
            self.status = status
            self.payload_hash = payload_hash
            self.sync_status = sync_status if isinstance(sync_status, str) else sync_status.value
            self.attendance_record_id = attendance_record_id
            self.submitted_by_id = submitted_by_id
            self.client_timestamp = client_timestamp or datetime.now(timezone.utc)
            self.server_timestamp = server_timestamp or datetime.now(timezone.utc)
            self.error_message = error_message
            self.created_at = created_at or datetime.now(timezone.utc)
            self.updated_at = updated_at or datetime.now(timezone.utc)

        def __repr__(self):
            return (
                f"<SyncEvent id={self.id} event_id='{self.event_id}' "
                f"session='{self.session_code}' student='{self.student_institutional_id}' "
                f"status='{self.sync_status}'>"
            )
