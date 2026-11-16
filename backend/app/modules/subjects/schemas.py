"""
RIT Sync Vision - Subject Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SubjectBase(BaseModel):
    """Base subject schema containing shared attributes."""
    subject_code: str = Field(..., min_length=1, max_length=50, description="Unique institutional course/subject code (e.g. CS101, MAT202)")
    name: str = Field(..., min_length=1, max_length=100, description="Subject title or course name")
    department: Optional[str] = Field(None, max_length=100, description="Academic department offering the subject")
    description: Optional[str] = Field(None, max_length=255, description="Subject description or syllabus overview")
    is_active: bool = Field(default=True, description="Subject active status")


class SubjectCreate(SubjectBase):
    """Schema for registering a new subject."""
    pass


class SubjectUpdate(BaseModel):
    """Schema for updating subject attributes."""
    subject_code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class SubjectResponse(BaseModel):
    """
    Public subject representation.
    """
    id: int
    subject_code: str
    name: str
    department: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
