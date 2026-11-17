"""
RIT Sync Vision - User Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from backend.app.modules.users.models import UserRole


class UserBase(BaseModel):
    """Base user schema containing common attributes."""
    email: str = Field(..., description="User corporate or institutional email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    full_name: str = Field(..., min_length=1, max_length=100, description="Full legal or display name")
    role: UserRole = Field(default=UserRole.TEACHER, description="Assigned role (admin or teacher)")
    is_active: bool = Field(default=True, description="Account active status")


class UserCreate(UserBase):
    """Schema for creating a new user (admin-only operation)."""
    password: str = Field(..., min_length=8, description="Initial plain text password")


class UserUpdate(BaseModel):
    """Schema for updating existing user details."""
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(BaseModel):
    """
    Public user representation.
    CRITICAL: Never exposes passwords or password hashes.
    """
    id: int
    email: str
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
