"""
Reliability regression tests for the AI pipeline (gap-analysis fixes).

Covers: zero-usable-track crash, camera fault, teacher stop, recorded video end,
permit validation, Haar fallback, fragmentation vs conflict, in-track identity switch,
model-version mismatch, NOT_OBSERVED != ABSENT invariant and log auditing.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import cv2
import numpy as np

from shared.constants import AttendanceCandidateState, MatchState, ReasonCode, SessionState
from shared.schemas import BoundingBox, EnrolledTemplate, FaceQualityResult, SessionContext
from ai_engine.camera_input import CameraInputAdapter
from ai_engine.decision_engine.attendance_decision import AttendanceDecisionEngine
from ai_engine.detection import face_detector as face_detector_module
from ai_engine.detection.face_detector import FaceDetector
from ai_engine.pipeline import AIEnginePipeline
from ai_engine.privacy.frame_handler import PrivacyAuditor
from ai_engine.privacy.session_guard import SessionGuard
from ai_engine.tracking.track_manager import TrackEvidence

try:
    from skimage import data as sk_data
except ImportError:  # pragma: no cover
    sk_data = None

ALLOWED_CANDIDATE_STATES = {
    AttendanceCandidateState.PRESENT_CANDIDATE,
    AttendanceCandidateState.NEEDS_REVIEW,
    AttendanceCandidateState.NOT_OBSERVED,
}


def unit_vec(seed: int, dim: int = 128) -> list:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    v /= np.linalg.norm(v)
    return [float(x) for x in v]


def ctx(**overrides) -> SessionContext:
    base = dict(
        session_id="SESS_T",
        class_id="CSE-F",
        subject_id="CS301",
        teacher_id="TCH_01",
        permit_id="PERMIT_1",
        duration_seconds=30,
    )
    base.update(overrides)
    return SessionContext(**base)


def face_frame(size=(640, 480)) -> np.ndarray:
    img = cv2.cvtColor(sk_data.astronaut(), cv2.COLOR_RGB2BGR)
    return cv2.resize(img, size)


class StaticFrameAdapter(CameraInputAdapter):
    """Live-like adapter that yields a fixed frame, optionally failing after N frames."""

    def __init__(self, frame, fail_after=None, total=None):
        super().__init__(source="synthetic", fps_target=1000)
        self.source_kind = self.SOURCE_FILE  # media-time window, no sleeping
        self._frame = frame
        self._fail_after = fail_after
        self._total = total
        self._n = 0

    def start_capture(self):
        self.fault = None
        self.stopped_by_teacher = False
        self._stop_event.clear()
        self._is_capturing = True
        self._cap = mock.MagicMock()
        self._cap.isOpened.return_value = True
        self._cap.get.return_value = 15.0
        return True

    def _read_frame(self):
        self._n += 1
        if self._fail_after is not None and self._n > self._fail_after:
            return False, None
        if self._total is not None and self._n > self._total:
            return False, None
        return True, self._frame.copy()


def good_q():
    return FaceQualityResult(
        is_usable=True, quality_score=0.9, blur_score=150, brightness_score=120, face_size_pixels=80
    )


def bad_q():
    return FaceQualityResult(
        is_usable=False,
        quality_score=0.2,
        blur_score=5,
        brightness_score=120,
        face_size_pixels=20,
        reason_codes=[ReasonCode.FACE_TOO_SMALL, ReasonCode.INSUFFICIENT_QUALITY],
    )


BOX = BoundingBox(x=10, y=10, width=80, height=80)


class TestDecisionEngineFixes(unittest.TestCase):
    def setUp(self):
        self.engine = AttendanceDecisionEngine(min_evidence_frames=3, similarity_threshold=0.65)
        self.templates = [
            EnrolledTemplate(student_id=f"S{i}", student_name=f"N{i}", embedding=unit_vec(i),
                             model_version="test", created_at="2026-11-18T00:00:00Z")
            for i in (1, 2, 3)
        ]
        self.roster = ["S1", "S2", "S3"]

    def test_track_with_zero_usable_frames_does_not_crash(self):
        trk = TrackEvidence("TRK_X")
        for f in range(4):
            trk.add_observation(bad_q(), None, BOX, frame_index=f)
        cands, obs = self.engine.process_tracks([trk], self.templates, self.roster, model_version="test")
        self.assertEqual(obs[0].evidence_count, 0)
        self.assertEqual(obs[0].total_observations, 4)
        self.assertEqual(obs[0].match_state, MatchState.INSUFFICIENT_QUALITY)
        self.assertIn(ReasonCode.FACE_TOO_SMALL, obs[0].reason_codes)
        self.assertTrue(all(c.candidate_state == AttendanceCandidateState.NOT_OBSERVED for c in cands))

    def test_fragmented_tracks_are_merged_not_conflicted(self):
        a, b = TrackEvidence("TRK_A"), TrackEvidence("TRK_B")
        for f in range(0, 2):
            a.add_observation(good_q(), unit_vec(1), BOX, frame_index=f)
        for f in range(10, 12):
            b.add_observation(good_q(), unit_vec(1), BOX, frame_index=f)
        cands, _ = self.engine.process_tracks([a, b], self.templates, self.roster, model_version="test")
        s1 = next(c for c in cands if c.student_id == "S1")
        self.assertEqual(s1.candidate_state, AttendanceCandidateState.PRESENT_CANDIDATE)
        self.assertEqual(s1.evidence_count, 4)
        self.assertNotIn(ReasonCode.CONFLICTING_IDENTITY, s1.reason_codes)
        self.assertNotIn(ReasonCode.INSUFFICIENT_EVIDENCE, s1.reason_codes)
        self.assertEqual(sum(1 for c in cands if c.student_id == "S1"), 1)

    def test_simultaneous_tracks_for_same_student_conflict(self):
        a, b = TrackEvidence("TRK_A"), TrackEvidence("TRK_B")
        for f in range(0, 4):
            a.add_observation(good_q(), unit_vec(1), BOX, frame_index=f)
            b.add_observation(good_q(), unit_vec(1), BOX, frame_index=f)
        cands, _ = self.engine.process_tracks([a, b], self.templates, self.roster, model_version="test")
        s1 = next(c for c in cands if c.student_id == "S1")
        self.assertEqual(s1.candidate_state, AttendanceCandidateState.NEEDS_REVIEW)
        self.assertIn(ReasonCode.CONFLICTING_IDENTITY, s1.reason_codes)

    def test_identity_switch_inside_track_is_flagged(self):
        trk = TrackEvidence("TRK_SWAP")
        for f in range(3):
            trk.add_observation(good_q(), unit_vec(1), BOX, frame_index=f)
        for f in range(3, 6):
            trk.add_observation(good_q(), unit_vec(2), BOX, frame_index=f)
        # Use a low threshold so the averaged embedding still matches someone
        engine = AttendanceDecisionEngine(min_evidence_frames=3, similarity_threshold=0.5, margin_threshold=0.0)
        cands, obs = engine.process_tracks([trk], self.templates, self.roster, model_version="test")
        self.assertIn(ReasonCode.CONFLICTING_IDENTITY, obs[0].reason_codes)
        self.assertNotEqual(obs[0].match_state, MatchState.MATCHED)
        self.assertFalse(any(c.candidate_state == AttendanceCandidateState.PRESENT_CANDIDATE for c in cands))

    def test_model_version_mismatch_never_matches(self):
        trk = TrackEvidence("TRK_1")
        for f in range(5):
            trk.add_observation(good_q(), unit_vec(1), BOX, frame_index=f)
        cands, obs = self.engine.process_tracks([trk], self.templates, self.roster, model_version="other")
        self.assertIn(ReasonCode.MODEL_VERSION_MISMATCH, obs[0].reason_codes)
        self.assertIsNone(obs[0].candidate_student_id)
        self.assertFalse(any(c.candidate_state == AttendanceCandidateState.PRESENT_CANDIDATE for c in cands))

    def test_candidate_states_never_absent(self):
        trk = TrackEvidence("TRK_1")
        for f in range(5):
            trk.add_observation(good_q(), unit_vec(1), BOX, frame_index=f)
        cands, _ = self.engine.process_tracks([trk], self.templates, self.roster, model_version="test")
        self.assertEqual(len(cands), len(self.roster))
        for c in cands:
            self.assertIn(c.candidate_state, ALLOWED_CANDIDATE_STATES)
            self.assertNotEqual(c.candidate_state.value, "ABSENT")


class TestSessionGuard(unittest.TestCase):
    def test_missing_permit_rejected(self):
        ok, reasons = SessionGuard().validate(ctx(permit_id="  "))
        self.assertFalse(ok)
        self.assertEqual(reasons, [ReasonCode.PERMIT_INVALID])

    def test_expired_permit_rejected(self):
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        ok, reasons = SessionGuard().validate(ctx(permit_expires_at=past))
        self.assertFalse(ok)
        self.assertEqual(reasons, [ReasonCode.PERMIT_EXPIRED])

    def test_verifier_is_consulted(self):
        ok, _ = SessionGuard(permit_verifier=lambda c: c.permit_id == "GOOD").validate(ctx())
        self.assertFalse(ok)
        ok, _ = SessionGuard(permit_verifier=lambda c: c.permit_id == "PERMIT_1").validate(ctx())
        self.assertTrue(ok)

    def test_window_must_be_30_to_120_seconds(self):
        with self.assertRaises(Exception):
            ctx(duration_seconds=5)
        with self.assertRaises(Exception):
            ctx(duration_seconds=121)


@unittest.skipIf(sk_data is None, "scikit-image not installed")
class TestPipelineEndToEnd(unittest.TestCase):
    def setUp(self):
        self.pipeline = AIEnginePipeline(encoder_backend="gradient")

    def test_real_face_sequence_completes(self):
        adapter = StaticFrameAdapter(face_frame(), total=40)
        result = self.pipeline.process_session(ctx(), adapter, [], ["S1", "S2"])
        self.assertEqual(result.status, SessionState.COMPLETED)
        self.assertGreater(result.total_tracks_detected, 0)
        self.assertIn("encoder=gradient_v1", result.model_version)
        self.assertIn("similarity_threshold", result.config)
        for c in result.candidates:
            self.assertEqual(c.candidate_state, AttendanceCandidateState.NOT_OBSERVED)

    def test_small_faces_only_regression(self):
        """Previously crashed: tracks with zero usable frames made the whole session FAILED."""
        tiny = cv2.resize(face_frame(), (160, 120))
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[180:300, 240:400] = tiny
        adapter = StaticFrameAdapter(frame, total=20)
        result = self.pipeline.process_session(ctx(), adapter, [], ["S1"])
        self.assertEqual(result.status, SessionState.COMPLETED)

    def test_enrolled_student_present_then_camera_fault_downgrades(self):
        frame = face_frame()
        # Enroll the visible face with the same encoder and pipeline detector
        det = self.pipeline.detector.detect_faces(frame)
        usable = [d for d in det if d.quality.is_usable]
        if not usable:
            self.skipTest("Sample face not usable under current quality thresholds")
        emb = self.pipeline.encoder.encode(usable[0].face_crop, enforce_quality=False)
        tmpl = EnrolledTemplate(student_id="S1", student_name="Astro", embedding=emb,
                                model_version=self.pipeline.encoder.model_version,
                                created_at="2026-11-18T00:00:00Z")

        ok = self.pipeline.process_session(ctx(), StaticFrameAdapter(frame, total=10), [tmpl], ["S1"])
        self.assertEqual(ok.status, SessionState.COMPLETED)
        s1 = next(c for c in ok.candidates if c.student_id == "S1")
        self.assertEqual(s1.candidate_state, AttendanceCandidateState.PRESENT_CANDIDATE)

        # Same scene, but the camera dies after 6 frames (first read fails -> fault)
        bad = StaticFrameAdapter(frame, fail_after=6)
        bad.source_kind = bad.SOURCE_LIVE
        bad.fps_target = 1000
        res = self.pipeline.process_session(ctx(), bad, [tmpl], ["S1"])
        self.assertEqual(res.status, SessionState.FAILED)
        self.assertIn(ReasonCode.CAMERA_DISCONNECTED, res.fault_reasons)
        s1 = next(c for c in res.candidates if c.student_id == "S1")
        self.assertEqual(s1.candidate_state, AttendanceCandidateState.NEEDS_REVIEW)
        self.assertIn(ReasonCode.CAMERA_DISCONNECTED, s1.reason_codes)

    def test_teacher_stop(self):
        adapter = StaticFrameAdapter(face_frame(), total=400)
        pipeline = AIEnginePipeline(encoder_backend="gradient", progress_every_n_frames=5)
        states = []

        def on_progress(p):
            states.append(p["state"])
            if p.get("frames_processed", 0) >= 5:
                adapter.request_stop()

        result = pipeline.process_session(ctx(), adapter, [], ["S1"], on_progress=on_progress)
        self.assertEqual(result.status, SessionState.STOPPED)
        self.assertIn(ReasonCode.CAPTURE_STOPPED_BY_TEACHER, result.fault_reasons)
        self.assertLess(result.total_frames_processed, 400)
        self.assertEqual(states[0], SessionState.INITIALIZING.value)
        self.assertEqual(states[-1], SessionState.STOPPED.value)

    def test_unauthorized_session_never_opens_camera(self):
        adapter = StaticFrameAdapter(face_frame(), total=10)
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        result = self.pipeline.process_session(ctx(permit_expires_at=past), adapter, [], ["S1"])
        self.assertEqual(result.status, SessionState.FAILED)
        self.assertIn(ReasonCode.PERMIT_EXPIRED, result.fault_reasons)
        self.assertEqual(result.total_frames_processed, 0)
        self.assertEqual(adapter._n, 0)
        self.assertEqual(result.candidates, [])

    def test_recorded_video_end_is_not_a_fault(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "clip.avi")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 15, (640, 480))
            if not writer.isOpened():
                self.skipTest("No video writer codec available")
            frame = face_frame()
            for _ in range(15):
                writer.write(frame)
            writer.release()

            adapter = CameraInputAdapter(source=path, fps_target=15)
            result = self.pipeline.process_session(ctx(), adapter, [], ["S1"])
            self.assertEqual(result.status, SessionState.COMPLETED)
            self.assertEqual(result.fault_reasons, [])
            self.assertGreater(result.total_frames_processed, 0)

    def test_haar_fallback_detects_faces(self):
        with mock.patch.object(face_detector_module, "YUNET_MODEL", "missing_model.onnx"):
            det = FaceDetector()
        self.assertIn(det.backend_name, ("haar_frontalface_default", "skimage_lbp_frontal_face"))
        self.assertTrue(det.is_ready)
        self.assertFalse(det.supports_landmarks)
        self.assertGreaterEqual(len(det.detect_faces(face_frame())), 1)

    def test_detections_release_frame_memory(self):
        dets = self.pipeline.detector.detect_faces(face_frame())
        self.assertTrue(dets)
        for d in dets:
            d.release()
            self.assertIsNone(d.face_crop)
            self.assertIsNone(d.source_frame)


class TestLogAudit(unittest.TestCase):
    def test_embedding_dump_in_logs_is_detected(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "logs"))
            with open(os.path.join(root, "logs", "app.log"), "w") as f:
                f.write("INFO session ok\n")
            self.assertTrue(PrivacyAuditor.audit_logs_for_biometrics(root)[0])
            with open(os.path.join(root, "logs", "app.log"), "a") as f:
                f.write("DEBUG emb=" + ", ".join(f"{x:.4f}" for x in unit_vec(7)) + "\n")
            clean, violations = PrivacyAuditor.audit_logs_for_biometrics(root)
            self.assertFalse(clean)
            self.assertEqual(len(violations), 1)

    def test_media_file_in_logs_is_detected(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "logs"))
            open(os.path.join(root, "logs", "frame.jpg"), "wb").close()
            clean, _ = PrivacyAuditor.audit_storage_cleanliness(root)
            self.assertFalse(clean)


if __name__ == "__main__":
    unittest.main()
