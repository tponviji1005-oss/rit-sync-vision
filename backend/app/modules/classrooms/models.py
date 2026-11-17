"""
RIT Sync Vision - Classroom Data Model
"""

from datetime import datetime, timezone

try:
    from sqlalchemy import Boolean, Column, DateTime, Integer, String
    from backend.app.database.base import Base

    class Classroom(Base):
        """
        SQLAlchemy model representing physical or logical classrooms.
        CRITICAL: Never store face images, biometric data, or raw video footage here.
        """
        __tablename__ = "classrooms"

        id = Column(Integer, primary_key=True, index=True)
        room_number = Column(String(50), unique=True, index=True, nullable=False)
        name = Column(String(100), nullable=False)
        capacity = Column(Integer, nullable=True, default=60)
        camera_stream_url = Column(String(255), nullable=True)
        is_active = Column(Boolean, default=True, nullable=False)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        updated_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

        def __repr__(self):
            return f"<Classroom id={self.id} room_number='{self.room_number}' name='{self.name}'>"

except Exception:
    class Classroom:
        """Fallback Classroom model matching the SQLAlchemy schema."""
        __tablename__ = "classrooms"

        def __init__(
            self,
            id=None,
            room_number="",
            name="",
            capacity=60,
            camera_stream_url=None,
            is_active=True,
            created_at=None,
            updated_at=None,
        ):
            self.id = id
            self.room_number = room_number
            self.name = name
            self.capacity = capacity
            self.camera_stream_url = camera_stream_url
            self.is_active = is_active
            self.created_at = created_at or datetime.now(timezone.utc)
            self.updated_at = updated_at or datetime.now(timezone.utc)

        def __repr__(self):
            return f"<Classroom id={self.id} room_number='{self.room_number}' name='{self.name}'>"
