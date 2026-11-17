"""
RIT Sync Vision - Offline Synchronization Schemas
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.modules.synchronization.models import SyncEventStatus


class SyncOperationItem(BaseModel):
    """Single offline attendance operation item within a batch submission."""
    event_id: str = Field(..., min_length=1, max_length=100, description="Stable unique client-generated UUID/identifier")
    session_id: str = Field(..., min_length=1, description="Capture session ID or session_code")
    student_id: str = Field(..., min_length=1, max_length=50, description="Institutional student ID string")
    event_type: str = Field(default="RECORD_ATTENDANCE", description="Event type identifier")
    status: str = Field(..., description="Attendance status (e.g. PRESENT, ABSENT)")
    notes: Optional[str] = Field(default=None, max_length=500, description="Optional teacher remarks / notes")
    client_timestamp: Optional[datetime] = Field(default=None, description="Client-side timestamp when event was queued")


class SyncBatchRequest(BaseModel):
    """Batch request carrying offline attendance events."""
    events: List[SyncOperationItem] = Field(..., min_length=1, description="List of offline attendance events to sync")


class SyncOperationResult(BaseModel):
    """Outcome of processing an individual sync event."""
    event_id: str
    session_id: str
    student_id: str
    status: SyncEventStatus
    message: str
    attendance_record_id: Optional[int] = None
    server_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncBatchResponse(BaseModel):
    """Aggregated batch response acknowledging synchronized events."""
    total_events: int
    synced_count: int
    duplicate_count: int
    conflict_count: int
    rejected_count: int
    results: List[SyncOperationResult]


class SyncEventResponse(BaseModel):
    """Detailed response for a single stored synchronization event."""
    id: int
    event_id: str
    session_id: int
    session_code: Optional[str] = None
    student_id: int
    student_institutional_id: str
    event_type: str
    status: str
    sync_status: str
    attendance_record_id: Optional[int] = None
    submitted_by_id: int
    client_timestamp: datetime
    server_timestamp: datetime
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
