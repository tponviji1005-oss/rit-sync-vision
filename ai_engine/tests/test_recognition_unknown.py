"""
Unit tests for Open-Set Face Recognition and UNKNOWN Detection
"""

import unittest
import numpy as np
from shared.constants import MatchState, ReasonCode
from shared.schemas import EnrolledTemplate
from ai_engine.recognition.unknown_detector import UnknownDetector


def create_normalized_vec(seed_val: float, length: int = 128) -> list:
    np.random.seed(int(seed_val * 1000))
    v = np.random.randn(length).astype(np.float32)
    v /= np.linalg.norm(v)
    return [round(float(x), 6) for x in v]


class TestRecognitionUnknown(unittest.TestCase):
    def setUp(self):
        self.detector = UnknownDetector(similarity_threshold=0.65, margin_threshold=0.10)
        self.t1 = EnrolledTemplate(
            student_id="STU01",
            student_name="Alice",
            embedding=create_normalized_vec(1.0),
            created_at="2026-11-16T10:00:00Z",
        )
        self.t2 = EnrolledTemplate(
            student_id="STU02",
            student_name="Bob",
            embedding=create_normalized_vec(2.0),
            created_at="2026-11-16T10:00:00Z",
        )
        self.templates = [self.t1, self.t2]

    def test_matched_known_student(self):
        # Query vector is almost identical to Alice (high cosine similarity)
        q = [x + 0.001 for x in self.t1.embedding]
        norm = np.linalg.norm(q)
        q = [float(x / norm) for x in q]

        res = self.detector.identify(q, self.templates)
        self.assertEqual(res.match_state, MatchState.MATCHED)
        self.assertEqual(res.student_id, "STU01")
        self.assertGreaterEqual(res.confidence, 0.95)
        self.assertEqual(res.reason_codes, [])

    def test_unknown_unenrolled_person(self):
        # Orthogonal random vector far from Alice and Bob
        q = create_normalized_vec(999.0)
        res = self.detector.identify(q, self.templates)
        self.assertEqual(res.match_state, MatchState.UNKNOWN)
        self.assertIsNone(res.student_id)
        self.assertIn(ReasonCode.LOW_MATCH_CONFIDENCE, res.reason_codes)

    def test_ambiguous_margin_needs_review(self):
        # Query that is equidistant to Alice and Bob
        v1 = np.array(self.t1.embedding)
        v2 = np.array(self.t2.embedding)
        mid = (v1 + v2) / 2.0
        mid /= np.linalg.norm(mid)
        q = [round(float(x), 6) for x in mid]

        # Use detector with lower threshold to test margin check
        custom_det = UnknownDetector(similarity_threshold=0.40, margin_threshold=0.10)
        res = custom_det.identify(q, self.templates)

        # Difference between Alice and Bob similarity should be close to 0 (< 0.10)
        self.assertEqual(res.match_state, MatchState.NEEDS_REVIEW)
        self.assertIn(ReasonCode.AMBIGUOUS_MATCH, res.reason_codes)

    def test_empty_embedding_insufficient_quality(self):
        res = self.detector.identify(None, self.templates)
        self.assertEqual(res.match_state, MatchState.INSUFFICIENT_QUALITY)


if __name__ == "__main__":
    unittest.main()
