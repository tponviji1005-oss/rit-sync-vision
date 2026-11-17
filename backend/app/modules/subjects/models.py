"""
RIT Sync Vision - Subject Data Model
"""

from datetime import datetime, timezone

try:
    from sqlalchemy import Boolean, Column, DateTime, Integer, String
    from backend.app.database.base import Base

    class Subject(Base):
        """
        SQLAlchemy model representing academic subjects/courses.
        """
        __tablename__ = "subjects"

        id = Column(Integer, primary_key=True, index=True)
        subject_code = Column(String(50), unique=True, index=True, nullable=False)
        name = Column(String(100), nullable=False)
        department = Column(String(100), nullable=True)
        description = Column(String(255), nullable=True)
        is_active = Column(Boolean, default=True, nullable=False)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
        updated_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

        def __repr__(self):
            return f"<Subject id={self.id} code='{self.subject_code}' name='{self.name}'>"

except Exception:
    class Subject:
        """Fallback Subject model matching the SQLAlchemy schema."""
        __tablename__ = "subjects"

        def __init__(
            self,
            id=None,
            subject_code="",
            name="",
            department=None,
            description=None,
            is_active=True,
            created_at=None,
            updated_at=None,
        ):
            self.id = id
            self.subject_code = subject_code
            self.name = name
            self.department = department
            self.description = description
            self.is_active = is_active
            self.created_at = created_at or datetime.now(timezone.utc)
            self.updated_at = updated_at or datetime.now(timezone.utc)

        def __repr__(self):
            return f"<Subject id={self.id} code='{self.subject_code}' name='{self.name}'>"
