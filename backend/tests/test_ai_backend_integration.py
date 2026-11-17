"""
Backend-AI Integration Tests
Verifies that AI Engine results successfully integrate with Vijayalakshmi's backend layer.
"""

import unittest
from shared.schemas import SessionContext, EnrolledTemplate
from shared.constants import SessionState, AttendanceCandidateState
from backend.app.modules.ai_processing.service import ai_service
from backend.app.modules.ai_processing.router import (
    get_ai_health,
    process_capture_session,
    ProcessSessionRequest,
)


class TestBackendAIIntegration(unittest.TestCase):
    def test_ai_health_check(self):
        health = get_ai_health(camera_source="synthetic")
        self.assertTrue(health.camera_ready)
        self.assertTrue(health.model_ready)
        self.assertEqual(health.overall_status, "HEALTHY")
        self.assertIn("camera", health.details)
        self.assertIn("detector", health.details)

    def test_ai_process_session(self):
        ctx = SessionContext(
            session_id="SESS_INTEGRATION_001",
            class_id="CSE-F",
            subject_id="CS301",
            teacher_id="TCH_01",
            permit_id="PERMIT_ABC_123",
            duration_seconds=1,
        )
        req = ProcessSessionRequest(
            session_context=ctx,
            camera_source="synthetic",
            enrolled_templates=[],
            roster_student_ids=["STU_001", "STU_002", "STU_003"],
            roster_names={
                "STU_001": "Alice",
                "STU_002": "Bob",
                "STU_003": "Charlie",
            },
        )

        result = process_capture_session(req)

        self.assertEqual(result.session_id, "SESS_INTEGRATION_001")
        self.assertEqual(result.status, SessionState.COMPLETED)
        self.assertGreater(result.total_frames_processed, 0)
        self.assertEqual(len(result.candidates), 3)

        # Enforce Core Rule: All non-observed roster students MUST be NOT_OBSERVED (Never ABSENT)
        for cand in result.candidates:
            self.assertEqual(cand.candidate_state, AttendanceCandidateState.NOT_OBSERVED)
            self.assertEqual(cand.evidence_count, 0)
            self.assertEqual(cand.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
