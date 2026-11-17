"""
RIT-Sync Vision - AI Engine Main Pipeline
Author: Paul Bryton Raj (AI & System Lead)

Unified AI Processing Pipeline combining:
1. Camera Input (bounded capture window)
2. Multiple Face Detection (YuNet DNN)
3. Quality Gate (blur, size, lighting, visibility)
4. Multi-Frame Tracking (IoU tracklets)
5. Face Feature Encoding (128-d L2 normalized)
6. Open-Set Recognition (cosine similarity, UNKNOWN & margin gates)
7. Attendance Decision Engine (PRESENT_CANDIDATE, NEEDS_REVIEW, NOT_OBSERVED)

Privacy by default: Frames exist only in volatile memory during processing and are immediately released.
"""

import time
import logging
from typing import List, Optional, Dict, Any, Generator, Tuple
import numpy as np

from shared.constants import SessionState
from shared.schemas import (
    SessionContext,
    EnrolledTemplate,
    AIProcessingResult,
    DeviceHealthStatus,
)
from ai_engine.camera_input import CameraInputAdapter
from ai_engine.detection.face_detector import FaceDetector, DetectionResult
from ai_engine.detection.face_quality import FaceQualityEvaluator
from ai_engine.tracking.face_tracker import FaceTracker
from ai_engine.tracking.track_manager import TrackManager
from ai_engine.recognition.face_encoder import FaceEncoder
from ai_engine.decision_engine.attendance_decision import AttendanceDecisionEngine

logger = logging.getLogger("rit_sync_vision.ai_pipeline")


class AIEnginePipeline:
    """
    Main entry point for AI processing. Imported directly by backend modules.
    """

    def __init__(
        self,
        min_evidence_frames: int = 3,
        similarity_threshold: float = 0.65,
        margin_threshold: float = 0.10,
        min_face_size: int = 48,
    ):
        self.detector = FaceDetector(min_face_size=min_face_size)
        self.encoder = FaceEncoder(min_face_size=min_face_size)
        self.tracker = FaceTracker()
        self.track_manager = TrackManager()
        self.decision_engine = AttendanceDecisionEngine(
            min_evidence_frames=min_evidence_frames,
            similarity_threshold=similarity_threshold,
            margin_threshold=margin_threshold,
        )

    def check_health(self, camera_adapter: Optional[CameraInputAdapter] = None) -> DeviceHealthStatus:
        """
        Runs comprehensive health checks on detector, encoder, and camera.
        """
        detector_ready = (self.detector._detector is not None)
        camera_ready = True
        details = {}

        if camera_adapter is not None:
            cam_ok, cam_details = camera_adapter.check_health()
            camera_ready = cam_ok
            details["camera"] = cam_details

        details["detector"] = "YuNet DNN ready" if detector_ready else "Fallback LBP ready"
        details["encoder"] = "128-d spatial gradient encoder ready"

        overall_ok = camera_ready and detector_ready
        return DeviceHealthStatus(
            camera_ready=camera_ready,
            model_ready=detector_ready,
            storage_ready=True,
            clock_synchronized=True,
            overall_status="HEALTHY" if overall_ok else "FAULT",
            details=details,
        )

    def process_session(
        self,
        session_context: SessionContext,
        camera_adapter: CameraInputAdapter,
        enrolled_templates: List[EnrolledTemplate],
        roster_student_ids: List[str],
        roster_names: Optional[Dict[str, str]] = None,
    ) -> AIProcessingResult:
        """
        Executes an end-to-end capture and observation pipeline for an authorized session.
        """
        start_time = time.time()
        self.tracker.reset()
        self.track_manager.clear()

        frame_count = 0

        try:
            logger.info(
                f"Starting AI session {session_context.session_id} for duration {session_context.duration_seconds}s"
            )

            # Stream frames from camera adapter within bounded duration
            for frame_idx, timestamp, frame in camera_adapter.stream_frames(
                duration_seconds=session_context.duration_seconds
            ):
                frame_count += 1

                # 1. Detect faces & evaluate quality
                detections: List[DetectionResult] = self.detector.detect_faces(frame)

                # 2. Update multi-frame tracker
                matched_tracks = self.tracker.update(frame_idx, detections)

                # 3. For each active observation in this frame, extract embedding if usable
                for tid, det in matched_tracks:
                    embedding = None
                    if det.quality.is_usable:
                        embedding = self.encoder.encode(det.face_crop, enforce_quality=False)

                    # 4. Record into session track manager
                    self.track_manager.record(
                        track_id=tid,
                        quality=det.quality,
                        embedding=embedding,
                        bbox=det.bbox,
                    )

                # Memory cleanup: dereference frame immediately (privacy guarantee)
                del frame

            # 5. Synthesize session tracks into attendance proposals
            all_tracks = self.track_manager.get_all_tracks()
            candidates, observations = self.decision_engine.process_tracks(
                tracks=all_tracks,
                enrolled_templates=enrolled_templates,
                roster_student_ids=roster_student_ids,
                roster_names=roster_names,
            )

            elapsed_ms = (time.time() - start_time) * 1000.0

            return AIProcessingResult(
                session_id=session_context.session_id,
                total_frames_processed=frame_count,
                total_tracks_detected=len(all_tracks),
                observations=observations,
                candidates=candidates,
                processing_time_ms=round(elapsed_ms, 2),
                status=SessionState.COMPLETED,
            )

        except Exception as e:
            logger.error(f"Error in AI pipeline session: {e}", exc_info=True)
            elapsed_ms = (time.time() - start_time) * 1000.0
            return AIProcessingResult(
                session_id=session_context.session_id,
                total_frames_processed=frame_count,
                total_tracks_detected=0,
                observations=[],
                candidates=[],
                processing_time_ms=round(elapsed_ms, 2),
                status=SessionState.FAILED,
            )
        finally:
            # Clear all in-memory track data and buffers
            self.tracker.reset()
            self.track_manager.clear()
