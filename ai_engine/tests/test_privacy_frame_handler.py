"""
Unit tests for Privacy and Frame Lifecycle
"""

import unittest
import os
import numpy as np
from ai_engine.privacy.frame_handler import EphemeralFrameContext, PrivacyAuditor


class TestPrivacyFrameHandler(unittest.TestCase):
    def test_ephemeral_frame_context(self):
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        ctx = EphemeralFrameContext(arr)
        with ctx as f:
            self.assertEqual(f.shape, (100, 100, 3))
        # After exit, frame is cleared
        self.assertIsNone(ctx.frame)

    def test_storage_privacy_audit(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        is_clean, violations = PrivacyAuditor.audit_storage_cleanliness(project_root)
        self.assertTrue(is_clean, f"Found persisted raw image/video files: {violations}")
        self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
