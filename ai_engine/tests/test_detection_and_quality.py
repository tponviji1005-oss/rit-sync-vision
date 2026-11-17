"""
Unit tests for Face Detection and Quality Gate
"""

import unittest
import numpy as np
import cv2
from ai_engine.detection.face_detector import FaceDetector
from ai_engine.detection.face_quality import FaceQualityEvaluator
from ai_engine.quality_check.blur_check import BlurChecker
from ai_engine.quality_check.lighting_check import LightingChecker
from ai_engine.quality_check.face_visibility import FaceVisibilityChecker
from shared.constants import ReasonCode


class TestDetectionAndQuality(unittest.TestCase):
    def setUp(self):
        self.detector = FaceDetector()
        self.evaluator = FaceQualityEvaluator(min_size_pixels=48)

    def test_empty_frame(self):
        empty = np.zeros((480, 640, 3), dtype=np.uint8)
        results = self.detector.detect_faces(empty)
        self.assertEqual(len(results), 0)

    def test_blur_checker_detects_blur(self):
        checker = BlurChecker(blur_threshold=50.0)
        # Sharp image with checkerboard/high contrast
        sharp = np.zeros((100, 100, 3), dtype=np.uint8)
        sharp[::2, ::2] = 255
        sharp[1::2, 1::2] = 255
        is_sharp, val = checker.evaluate(sharp)
        self.assertTrue(is_sharp)
        self.assertGreater(val, 50.0)

        # Uniform blurred image
        blurred = cv2.GaussianBlur(sharp, (25, 25), 10.0)
        is_sharp_blur, val_blur = checker.evaluate(blurred)
        self.assertFalse(is_sharp_blur)
        self.assertLess(val_blur, 50.0)

    def test_lighting_checker(self):
        checker = LightingChecker(min_brightness=40.0, max_brightness=225.0)
        dark = np.ones((80, 80, 3), dtype=np.uint8) * 15
        bright = np.ones((80, 80, 3), dtype=np.uint8) * 245
        good = np.ones((80, 80, 3), dtype=np.uint8) * 128

        self.assertFalse(checker.evaluate(dark)[0])
        self.assertFalse(checker.evaluate(bright)[0])
        self.assertTrue(checker.evaluate(good)[0])

    def test_face_visibility_too_small(self):
        checker = FaceVisibilityChecker(min_size_pixels=48)
        valid, reasons = checker.evaluate(x=100, y=100, w=30, h=30, frame_w=640, frame_h=480)
        self.assertFalse(valid)
        self.assertIn(ReasonCode.FACE_TOO_SMALL, reasons)

    def test_quality_evaluator_rejection(self):
        # Extremely dark small crop
        dark_crop = np.ones((32, 32, 3), dtype=np.uint8) * 10
        res = self.evaluator.evaluate(
            face_crop=dark_crop,
            bbox_x=10,
            bbox_y=10,
            bbox_w=32,
            bbox_h=32,
            frame_w=640,
            frame_h=480,
        )
        self.assertFalse(res.is_usable)
        self.assertIn(ReasonCode.FACE_TOO_SMALL, res.reason_codes)
        self.assertIn(ReasonCode.POOR_LIGHTING, res.reason_codes)


if __name__ == "__main__":
    unittest.main()
