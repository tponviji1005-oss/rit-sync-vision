"""
RIT-Sync Vision - AI Processing Service (Backend Adapter)
Author: Paul Bryton Raj & Pon Vijayalakshmi

Connects FastAPI backend requests with the internal AI Engine pipeline.
"""

from typing import List, Dict, Optional, Any
from shared.schemas import (
    SessionContext,
    EnrolledTemplate,
    AIProcessingResult,
    DeviceHealthStatus,
    FaceQualityResult,
)
from ai_engine.pipeline import AIEnginePipeline
from ai_engine.camera_input import CameraInputAdapter


class AIProcessingService:
    """
    Singleton-style service wrapping the AI Engine for backend route handlers.
    """

    def __init__(self):
        self.pipeline = AIEnginePipeline()

    def get_health(self, camera_source: Any = "synthetic") -> DeviceHealthStatus:
        adapter = CameraInputAdapter(source=camera_source)
        return self.pipeline.check_health(camera_adapter=adapter)

    def execute_session(
        self,
        session_context: SessionContext,
        camera_source: Any,
        enrolled_templates: List[EnrolledTemplate],
        roster_student_ids: List[str],
        roster_names: Optional[Dict[str, str]] = None,
    ) -> AIProcessingResult:
        """
        Executes bounded capture session and returns structured AI candidates.
        """
        adapter = CameraInputAdapter(source=camera_source)
        return self.pipeline.process_session(
            session_context=session_context,
            camera_adapter=adapter,
            enrolled_templates=enrolled_templates,
            roster_student_ids=roster_student_ids,
            roster_names=roster_names,
        )


ai_service = AIProcessingService()
