"""
RIT-Sync Vision - AI Processing API Router
Provides endpoints for AI health checks and session execution.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from shared.schemas import (
    SessionContext,
    EnrolledTemplate,
    AIProcessingResult,
    DeviceHealthStatus,
)
from backend.app.modules.ai_processing.service import ai_service

router = APIRouter(prefix="/api/v1/ai", tags=["AI Engine"])


class ProcessSessionRequest(BaseModel):
    session_context: SessionContext
    camera_source: str = "synthetic"  # "0" for default webcam, file path, or "synthetic"
    enrolled_templates: List[EnrolledTemplate] = []
    roster_student_ids: List[str] = []
    roster_names: Optional[Dict[str, str]] = None


@router.get("/health", response_model=DeviceHealthStatus)
def get_ai_health(camera_source: str = "synthetic"):
    """
    Validates readiness of camera, AI detection models, and feature extractors.
    Runs in threadpool.
    """
    try:
        source_val = int(camera_source) if camera_source.isdigit() else camera_source
        return ai_service.get_health(camera_source=source_val)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/process-session", response_model=AIProcessingResult)
def process_capture_session(req: ProcessSessionRequest):
    """
    Executes a bounded capture session and returns structured attendance proposals.
    Runs in threadpool.
    Non-negotiable rule: NOT_OBSERVED != ABSENT.
    """
    try:
        source_val = int(req.camera_source) if req.camera_source.isdigit() else req.camera_source
        result = ai_service.execute_session(
            session_context=req.session_context,
            camera_source=source_val,
            enrolled_templates=req.enrolled_templates,
            roster_student_ids=req.roster_student_ids,
            roster_names=req.roster_names,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI session execution error: {str(e)}")
