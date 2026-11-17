"""
Unit tests for CameraInputAdapter
"""

import unittest
from ai_engine.camera_input import CameraInputAdapter


class TestCameraInput(unittest.TestCase):
    def test_synthetic_camera_health(self):
        adapter = CameraInputAdapter(source="synthetic", capture_width=640, capture_height=480)
        healthy, details = adapter.check_health()
        self.assertTrue(healthy)
        self.assertEqual(details["status"], "ready")

    def test_synthetic_frame_streaming_bounded(self):
        adapter = CameraInputAdapter(source="synthetic", fps_target=30, capture_width=320, capture_height=240)
        frames_received = 0
        # Request short 0.2 second duration
        for idx, ts, frame in adapter.stream_frames(duration_seconds=1):
            frames_received += 1
            self.assertEqual(frame.shape, (240, 320, 3))
            if frames_received >= 5:
                adapter.stop_capture()
                break
        self.assertGreaterEqual(frames_received, 5)

    def test_invalid_device_health(self):
        # Index 99999 should fail cleanly without crashing
        adapter = CameraInputAdapter(source=99999)
        healthy, details = adapter.check_health()
        self.assertFalse(healthy)
        self.assertIn("error", details)


if __name__ == "__main__":
    unittest.main()
