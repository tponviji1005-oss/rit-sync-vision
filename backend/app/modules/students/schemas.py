"""
RIT Sync Vision - Student Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StudentBase(BaseModel):
    """Base student schema containing shared attributes."""
    student_id: str = Field(..., min_length=1, max_length=50, description="Unique institutional student identifier")
    first_name: str = Field(..., min_length=1, max_length=100, description="Student first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Student last name")
    email: Optional[str] = Field(None, description="Optional institutional email address")
    is_active: bool = Field(default=True, description="Student active status")
    is_enrolled: bool = Field(default=False, description="Face template enrollment status metadata")


class StudentCreate(StudentBase):
    """Schema for registering a new student record."""
    pass


class StudentUpdate(BaseModel):
    """Schema for updating student details."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_enrolled: Optional[bool] = None


class StudentResponse(BaseModel):
    """
    Public student representation.
    CRITICAL: Contains only metadata; never raw biometric data or templates.
    """
    id: int
    student_id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    is_active: bool
    is_enrolled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
