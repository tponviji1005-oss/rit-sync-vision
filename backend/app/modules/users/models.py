"""
RIT Sync Vision - User and Role Models
"""

from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role definitions for role-based authorization."""
    ADMIN = "admin"
    TEACHER = "teacher"


try:
    from sqlalchemy import Boolean, Column, DateTime, Integer, String
    from backend.app.database.base import Base

    class User(Base):
        """SQLAlchemy model representing application users."""
        __tablename__ = "users"

        id = Column(Integer, primary_key=True, index=True)
        email = Column(String(255), unique=True, index=True, nullable=False)
        username = Column(String(100), unique=True, index=True, nullable=False)
        full_name = Column(String(255), nullable=False)
        hashed_password = Column(String(255), nullable=False)
        role = Column(String(50), default=UserRole.TEACHER.value, nullable=False)
        is_active = Column(Boolean, default=True, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False,
        )

        def __repr__(self):
            return f"<User id={self.id} username='{self.username}' role='{self.role}'>"

except Exception:
    class User:
        """Fallback User model matching the SQLAlchemy schema."""
        __tablename__ = "users"

        def __init__(
            self,
            id=None,
            email="",
            username="",
            full_name="",
            hashed_password="",
            role=UserRole.TEACHER.value,
            is_active=True,
            created_at=None,
            updated_at=None,
        ):
            self.id = id
            self.email = email
            self.username = username
            self.full_name = full_name
            self.hashed_password = hashed_password
            self.role = role.value if isinstance(role, UserRole) else role
            self.is_active = is_active
            self.created_at = created_at or datetime.utcnow()
            self.updated_at = updated_at or datetime.utcnow()

        def __repr__(self):
            return f"<User id={self.id} username='{self.username}' role='{self.role}'>"
