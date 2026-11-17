"""
Unit tests for Attendance Decision Engine
"""

import unittest
import numpy as np
from shared.constants import AttendanceCandidateState, MatchState, ReasonCode
from shared.schemas import EnrolledTemplate, BoundingBox, FaceQualityResult
from ai_engine.tracking.track_manager import TrackEvidence
from ai_engine.decision_engine.attendance_decision import AttendanceDecisionEngine


def make_embedding(seed_val: float) -> list:
    np.random.seed(int(seed_val * 1000))
    v = np.random.randn(128).astype(np.float32)
    v /= np.linalg.norm(v)
    return [round(float(x), 6) for x in v]


class TestAttendanceDecision(unittest.TestCase):
    def setUp(self):
        self.engine = AttendanceDecisionEngine(min_evidence_frames=3, similarity_threshold=0.65)
        self.t1 = EnrolledTemplate(
            student_id="STU01",
            student_name="Alice",
            embedding=make_embedding(1.0),
            created_at="2026-11-16T10:00:00Z",
        )
        self.t2 = EnrolledTemplate(
            student_id="STU02",
            student_name="Bob",
            embedding=make_embedding(2.0),
            created_at="2026-11-16T10:00:00Z",
        )
        self.t3 = EnrolledTemplate(
            student_id="STU03",
            student_name="Charlie",
            embedding=make_embedding(3.0),
            created_at="2026-11-16T10:00:00Z",
        )
        self.templates = [self.t1, self.t2, self.t3]
        self.roster = ["STU01", "STU02", "STU03"]
        self.q_good = FaceQualityResult(
            is_usable=True, quality_score=0.9, blur_score=100, brightness_score=120, face_size_pixels=60
        )
        self.box = BoundingBox(x=10, y=10, width=50, height=50)

    def test_present_candidate_generation(self):
        # Alice observed in 4 frames with Alice's embedding
        trk = TrackEvidence("TRK_001")
        for _ in range(4):
            trk.add_observation(self.q_good, self.t1.embedding, self.box)

        candidates, obs = self.engine.process_tracks([trk], self.templates, self.roster)

        # Alice should be PRESENT_CANDIDATE
        alice_cand = next(c for c in candidates if c.student_id == "STU01")
        self.assertEqual(alice_cand.candidate_state, AttendanceCandidateState.PRESENT_CANDIDATE)
        self.assertGreaterEqual(alice_cand.confidence, 0.8)
        self.assertEqual(alice_cand.evidence_count, 4)

        # Bob and Charlie were NOT observed -> NOT_OBSERVED (Never ABSENT!)
        bob_cand = next(c for c in candidates if c.student_id == "STU02")
        self.assertEqual(bob_cand.candidate_state, AttendanceCandidateState.NOT_OBSERVED)
        self.assertEqual(bob_cand.evidence_count, 0)

    def test_low_evidence_needs_review(self):
        # Alice observed in only 1 frame (< 3 min frames)
        trk = TrackEvidence("TRK_001")
        trk.add_observation(self.q_good, self.t1.embedding, self.box)

        candidates, obs = self.engine.process_tracks([trk], self.templates, self.roster)
        alice_cand = next(c for c in candidates if c.student_id == "STU01")
        self.assertEqual(alice_cand.candidate_state, AttendanceCandidateState.NEEDS_REVIEW)
        self.assertIn(ReasonCode.INSUFFICIENT_EVIDENCE, alice_cand.reason_codes)

    def test_duplicate_tracks_route_to_review(self):
        # Two different tracks (TRK_1 and TRK_2) both matched Alice (e.g. proxy or camera glitch)
        trk1 = TrackEvidence("TRK_001")
        trk2 = TrackEvidence("TRK_002")
        for _ in range(4):
            trk1.add_observation(self.q_good, self.t1.embedding, self.box)
            trk2.add_observation(self.q_good, self.t1.embedding, self.box)

        candidates, obs = self.engine.process_tracks([trk1, trk2], self.templates, self.roster)

        alice_cand = next(c for c in candidates if c.student_id == "STU01")
        self.assertEqual(alice_cand.candidate_state, AttendanceCandidateState.NEEDS_REVIEW)
        self.assertIn(ReasonCode.DUPLICATE_CANDIDATE, alice_cand.reason_codes)


if __name__ == "__main__":
    unittest.main()
