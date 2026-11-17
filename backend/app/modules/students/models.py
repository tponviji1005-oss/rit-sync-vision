"""
RIT Sync Vision - Student Data Model
"""

from datetime import datetime, timezone

try:
    from sqlalchemy import Boolean, Column, DateTime, Integer, String
    from backend.app.database.base import Base

    class Student(Base):
        """
        SQLAlchemy model representing enrolled students.
        CRITICAL: Never store face images, raw biometric data, or face templates here.
        """
        __tablename__ = "students"

        id = Column(Integer, primary_key=True, index=True)
        student_id = Column(String(50), unique=True, index=True, nullable=False)
        first_name = Column(String(100), nullable=False)
        last_name = Column(String(100), nullable=False)
        email = Column(String(255), unique=True, index=True, nullable=True)
        is_active = Column(Boolean, default=True, nullable=False)
        is_enrolled = Column(Boolean, default=False, nullable=False)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        updated_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

        def __repr__(self):
            return f"<Student id={self.id} student_id='{self.student_id}' name='{self.first_name} {self.last_name}'>"

except Exception:
    class Student:
        """Fallback Student model matching the SQLAlchemy schema."""
        __tablename__ = "students"

        def __init__(
            self,
            id=None,
            student_id="",
            first_name="",
            last_name="",
            email=None,
            is_active=True,
            is_enrolled=False,
            created_at=None,
            updated_at=None,
        ):
            self.id = id
            self.student_id = student_id
            self.first_name = first_name
            self.last_name = last_name
            self.email = email
            self.is_active = is_active
            self.is_enrolled = is_enrolled
            self.created_at = created_at or datetime.now(timezone.utc)
            self.updated_at = updated_at or datetime.now(timezone.utc)

        def __repr__(self):
            return f"<Student id={self.id} student_id='{self.student_id}' name='{self.first_name} {self.last_name}'>"
