"""
RIT-Sync Vision - AI Engine Package
"""

from ai_engine.pipeline import AIEnginePipeline
from ai_engine.camera_input import CameraInputAdapter
from ai_engine.detection.face_detector import FaceDetector
from ai_engine.detection.face_quality import FaceQualityEvaluator
from ai_engine.tracking.face_tracker import FaceTracker
from ai_engine.tracking.track_manager import TrackManager
from ai_engine.recognition.face_encoder import FaceEncoder
from ai_engine.recognition.face_matcher import FaceMatcher
from ai_engine.recognition.unknown_detector import UnknownDetector
from ai_engine.decision_engine.attendance_decision import AttendanceDecisionEngine
from ai_engine.enrollment import FaceEnroller, EnrollmentResult
from ai_engine.privacy.session_guard import SessionGuard

__all__ = [
    "AIEnginePipeline",
    "CameraInputAdapter",
    "FaceDetector",
    "FaceQualityEvaluator",
    "FaceTracker",
    "TrackManager",
    "FaceEncoder",
    "FaceMatcher",
    "UnknownDetector",
    "AttendanceDecisionEngine",
    "FaceEnroller",
    "EnrollmentResult",
    "SessionGuard",
]
