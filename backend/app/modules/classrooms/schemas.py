"""
RIT Sync Vision - Classroom Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ClassroomBase(BaseModel):
    """Base classroom schema containing shared attributes."""
    room_number: str = Field(..., min_length=1, max_length=50, description="Unique room identifier or code (e.g. CR-101, LH-2)")
    name: str = Field(..., min_length=1, max_length=100, description="Classroom or hall name")
    capacity: Optional[int] = Field(60, ge=1, description="Seating capacity")
    camera_stream_url: Optional[str] = Field(None, max_length=255, description="Authorized camera RTSP or stream URL")
    is_active: bool = Field(default=True, description="Classroom active status")


class ClassroomCreate(ClassroomBase):
    """Schema for registering a new classroom."""
    pass


class ClassroomUpdate(BaseModel):
    """Schema for updating classroom attributes."""
    room_number: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    capacity: Optional[int] = Field(None, ge=1)
    camera_stream_url: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class ClassroomResponse(BaseModel):
    """
    Public classroom representation.
    CRITICAL: Never exposes raw video frames or biometric credentials.
    """
    id: int
    room_number: str
    name: str
    capacity: Optional[int] = None
    camera_stream_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
