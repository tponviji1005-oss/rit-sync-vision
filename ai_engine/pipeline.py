"""
RIT-Sync Vision - AI Engine Main Pipeline
Author: Paul Bryton Raj (AI & System Lead)

Unified AI Processing Pipeline combining:
0. Session authorization guard (no valid permit -> no capture)
1. Camera Input (bounded capture window, fault + teacher-stop aware)
2. Multiple Face Detection (YuNet DNN, Haar fallback)
3. Quality Gate (blur, size, lighting, visibility)
4. Multi-Frame Tracking (IoU tracklets)
5. Face Feature Encoding (SFace 128-d, or gradient dev baseline)
6. Open-Set Recognition (cosine similarity, UNKNOWN & margin gates)
7. Attendance Decision Engine (PRESENT_CANDIDATE, NEEDS_REVIEW, NOT_OBSERVED)

Privacy by default: frames exist only in volatile memory during processing and are released
after each frame. Track evidence holds embeddings and metadata only, and is cleared at session end.
"""

import os
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from shared.constants import SessionState, ReasonCode, AttendanceCandidateState
from shared.schemas import (
    SessionContext,
    EnrolledTemplate,
    AIProcessingResult,
    AttendanceCandidate,
    DeviceHealthStatus,
)
from ai_engine.camera_input import CameraInputAdapter
from ai_engine.detection.face_detector import FaceDetector, DetectionResult
from ai_engine.tracking.face_tracker import FaceTracker
from ai_engine.tracking.track_manager import TrackManager
from ai_engine.recognition.face_encoder import FaceEncoder
from ai_engine.decision_engine.attendance_decision import AttendanceDecisionEngine
from ai_engine.privacy.session_guard import SessionGuard, PermitVerifier

logger = logging.getLogger("rit_sync_vision.ai_pipeline")

ProgressCallback = Callable[[Dict[str, Any]], None]

REPO_ROOT = Path(__file__).resolve().parent.parent


class AIEnginePipeline:
    """
    Main entry point for AI processing. Imported directly by backend modules.
    """

    def __init__(
        self,
        min_evidence_frames: int = 3,
        similarity_threshold: Optional[float] = None,
        margin_threshold: Optional[float] = None,
        min_face_size: int = 48,
        encoder_backend: str = "auto",
        permit_verifier: Optional[PermitVerifier] = None,
        progress_every_n_frames: int = 15,
    ):
        """
        :param similarity_threshold: Open-set match threshold. None -> encoder's recommended value.
        :param margin_threshold: Best-vs-second margin. None -> encoder's recommended value.
        :param encoder_backend: "auto" | "sface" | "gradient"
        :param permit_verifier: Backend callable verifying capture permits (see SessionGuard).
        """
        self.detector = FaceDetector(min_face_size=min_face_size)
        self.encoder = FaceEncoder(min_face_size=min_face_size, backend=encoder_backend)
        self.tracker = FaceTracker()
        self.track_manager = TrackManager()
        self.session_guard = SessionGuard(permit_verifier=permit_verifier)
        self.progress_every_n_frames = max(1, progress_every_n_frames)

        rec = self.encoder.recommended_thresholds
        self.similarity_threshold = (
            similarity_threshold if similarity_threshold is not None else rec["similarity_threshold"]
        )
        self.margin_threshold = margin_threshold if margin_threshold is not None else rec["margin_threshold"]
        self.min_evidence_frames = min_evidence_frames
        self.min_face_size = min_face_size

        self.decision_engine = AttendanceDecisionEngine(
            min_evidence_frames=min_evidence_frames,
            similarity_threshold=self.similarity_threshold,
            margin_threshold=self.margin_threshold,
        )

    # ------------------------------------------------------------------ metadata

    @property
    def model_version(self) -> str:
        return f"detector={self.detector.backend_name};encoder={self.encoder.model_version}"

    def config_snapshot(self) -> Dict[str, Any]:
        return {
            "similarity_threshold": self.similarity_threshold,
            "margin_threshold": self.margin_threshold,
            "min_evidence_frames": self.min_evidence_frames,
            "min_face_size": self.min_face_size,
            "detector_conf_threshold": self.detector.conf_threshold,
            "tracker_iou_threshold": self.tracker.iou_threshold,
            "tracker_max_missed_frames": self.tracker.max_missed_frames,
            "identity_consistency": self.decision_engine.identity_consistency,
        }

    # ------------------------------------------------------------------ health

    @staticmethod
    def _storage_ready() -> bool:
        storage = REPO_ROOT / "storage"
        return storage.is_dir() and os.access(storage, os.W_OK)

    @staticmethod
    def _clock_plausible() -> bool:
        # Catches an unset/rolled-back RTC (e.g. 1970) on edge devices. Not a substitute for
        # permit-expiry and counter checks owned by the backend.
        return datetime.now(timezone.utc).year >= 2025

    def check_health(self, camera_adapter: Optional[CameraInputAdapter] = None) -> DeviceHealthStatus:
        """
        Runs health checks on detector, encoder, camera, storage and clock.
        """
        details: Dict[str, Any] = {}
        camera_ready = True
        if camera_adapter is not None:
            cam_ok, cam_details = camera_adapter.check_health()
            camera_ready = cam_ok
            details["camera"] = cam_details

        detector_ready = self.detector.is_ready
        details["detector"] = (
            f"{self.detector.backend_name} ready" if detector_ready else "NO DETECTION MODEL AVAILABLE"
        )
        details["encoder"] = f"{self.encoder.model_version} ready"
        if not self.encoder.is_identity_model:
            details["encoder_warning"] = (
                "Development gradient encoder in use; not a face recognition model. "
                "Run scripts/download_models.py to enable SFace."
            )
        details["model_version"] = self.model_version

        storage_ready = self._storage_ready()
        clock_ok = self._clock_plausible()

        overall_ok = camera_ready and detector_ready and storage_ready and clock_ok
        return DeviceHealthStatus(
            camera_ready=camera_ready,
            model_ready=detector_ready,
            storage_ready=storage_ready,
            clock_synchronized=clock_ok,
            overall_status="HEALTHY" if overall_ok else "FAULT",
            details=details,
        )

    # ------------------------------------------------------------------ session

    def _emit(self, cb: Optional[ProgressCallback], payload: Dict[str, Any]):
        if cb is None:
            return
        try:
            cb(payload)
        except Exception as e:  # A UI callback must never break attendance processing
            logger.warning("Progress callback raised %s; ignoring.", type(e).__name__)

    def _result(
        self,
        ctx: SessionContext,
        start_time: float,
        status: SessionState,
        frames: int = 0,
        tracks: int = 0,
        observations=None,
        candidates=None,
        faults: Optional[List[ReasonCode]] = None,
    ) -> AIProcessingResult:
        return AIProcessingResult(
            session_id=ctx.session_id,
            total_frames_processed=frames,
            total_tracks_detected=tracks,
            observations=observations or [],
            candidates=candidates or [],
            processing_time_ms=round((time.time() - start_time) * 1000.0, 2),
            status=status,
            fault_reasons=faults or [],
            model_version=self.model_version,
            config=self.config_snapshot(),
        )

    @staticmethod
    def _downgrade_for_fault(
        candidates: List[AttendanceCandidate], fault: ReasonCode
    ) -> List[AttendanceCandidate]:
        """After a capture fault, no candidate may be PRESENT_CANDIDATE without teacher review."""
        out = []
        for c in candidates:
            if c.candidate_state == AttendanceCandidateState.PRESENT_CANDIDATE:
                reasons = list(c.reason_codes)
                if fault not in reasons:
                    reasons.append(fault)
                c = c.model_copy(
                    update={"candidate_state": AttendanceCandidateState.NEEDS_REVIEW, "reason_codes": reasons}
                )
            out.append(c)
        return out

    def process_session(
        self,
        session_context: SessionContext,
        camera_adapter: CameraInputAdapter,
        enrolled_templates: List[EnrolledTemplate],
        roster_student_ids: List[str],
        roster_names: Optional[Dict[str, str]] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> AIProcessingResult:
        """
        Executes an end-to-end capture and observation pipeline for an authorized session.

        Status outcomes:
        - COMPLETED: window finished normally.
        - STOPPED:   teacher stopped capture early (candidates from the partial window are returned).
        - FAILED:    not authorized, no model, camera fault or internal error. Any partial
                     candidates are downgraded to NEEDS_REVIEW.
        Use camera_adapter.request_stop() from another thread for a teacher stop.
        """
        start_time = time.time()
        ctx = session_context
        self.tracker.reset()
        self.track_manager.clear()
        frame_count = 0

        self._emit(on_progress, {"session_id": ctx.session_id, "state": SessionState.INITIALIZING.value})

        # 0. Authorization
        authorized, auth_reasons = self.session_guard.validate(ctx)
        if not authorized:
            logger.warning("Session %s refused: %s", ctx.session_id, [r.value for r in auth_reasons])
            self._emit(on_progress, {"session_id": ctx.session_id, "state": SessionState.FAILED.value})
            return self._result(ctx, start_time, SessionState.FAILED, faults=auth_reasons)

        if not self.detector.is_ready:
            self._emit(on_progress, {"session_id": ctx.session_id, "state": SessionState.FAILED.value})
            return self._result(ctx, start_time, SessionState.FAILED, faults=[ReasonCode.MODEL_UNAVAILABLE])

        session_faults: List[ReasonCode] = []
        if enrolled_templates and not any(
            t.model_version == self.encoder.model_version for t in enrolled_templates
        ):
            session_faults.append(ReasonCode.MODEL_VERSION_MISMATCH)

        try:
            logger.info("Starting AI session %s for %ss", ctx.session_id, ctx.duration_seconds)
            self._emit(on_progress, {"session_id": ctx.session_id, "state": SessionState.CAPTURING.value})

            for frame_idx, _ts, frame in camera_adapter.stream_frames(duration_seconds=ctx.duration_seconds):
                frame_count += 1

                detections: List[DetectionResult] = self.detector.detect_faces(frame)
                matched_tracks = self.tracker.update(frame_idx, detections)

                for tid, det in matched_tracks:
                    embedding = None
                    if det.quality.is_usable:
                        embedding = self.encoder.encode(
                            det.face_crop,
                            enforce_quality=False,
                            source_frame=det.source_frame,
                            face_row=det.face_row,
                        )
                    self.track_manager.record(
                        track_id=tid,
                        quality=det.quality,
                        embedding=embedding,
                        bbox=det.bbox,
                        frame_index=frame_idx,
                    )

                # Privacy: release every reference to this frame's pixels
                for det in detections:
                    det.release()
                del detections, matched_tracks, frame

                if frame_count % self.progress_every_n_frames == 0:
                    self._emit(
                        on_progress,
                        {
                            "session_id": ctx.session_id,
                            "state": SessionState.CAPTURING.value,
                            "frames_processed": frame_count,
                            "active_tracks": len(self.tracker.active_tracks),
                            "total_tracks": len(self.track_manager.tracks),
                            "elapsed_ms": round((time.time() - start_time) * 1000.0, 1),
                        },
                    )

            if camera_adapter.fault is not None:
                session_faults.append(camera_adapter.fault)
            if camera_adapter.stopped_by_teacher:
                session_faults.append(ReasonCode.CAPTURE_STOPPED_BY_TEACHER)

            self._emit(on_progress, {"session_id": ctx.session_id, "state": SessionState.PROCESSING.value})

            all_tracks = self.track_manager.get_all_tracks()
            candidates, observations = self.decision_engine.process_tracks(
                tracks=all_tracks,
                enrolled_templates=enrolled_templates,
                roster_student_ids=roster_student_ids,
                roster_names=roster_names,
                model_version=self.encoder.model_version,
            )

            if camera_adapter.fault is not None:
                status = SessionState.FAILED
                candidates = self._downgrade_for_fault(candidates, camera_adapter.fault)
            elif camera_adapter.stopped_by_teacher:
                status = SessionState.STOPPED
            else:
                status = SessionState.COMPLETED

            self._emit(on_progress, {"session_id": ctx.session_id, "state": status.value})
            return self._result(
                ctx,
                start_time,
                status,
                frames=frame_count,
                tracks=len(all_tracks),
                observations=observations,
                candidates=candidates,
                faults=session_faults,
            )

        except Exception as e:
            # Log the error type only: messages may embed data values
            logger.error("Error in AI pipeline session %s: %s", ctx.session_id, type(e).__name__)
            self._emit(on_progress, {"session_id": ctx.session_id, "state": SessionState.FAILED.value})
            return self._result(ctx, start_time, SessionState.FAILED, frames=frame_count, faults=session_faults)
        finally:
            # Clear all in-memory track data and buffers
            self.tracker.reset()
            self.track_manager.clear()
