"""
Unit tests for Multi-Frame Tracking and Track Manager
"""

import unittest
import numpy as np
from shared.schemas import BoundingBox, FaceQualityResult
from ai_engine.detection.face_detector import DetectionResult
from ai_engine.tracking.face_tracker import FaceTracker, calculate_iou
from ai_engine.tracking.track_manager import TrackManager


class TestTracking(unittest.TestCase):
    def setUp(self):
        self.tracker = FaceTracker(iou_threshold=0.3, max_missed_frames=3)
        self.manager = TrackManager()

    def test_iou_calculation(self):
        b1 = BoundingBox(x=10, y=10, width=50, height=50)
        b2 = BoundingBox(x=10, y=10, width=50, height=50)
        # Identical boxes -> IoU = 1.0
        self.assertAlmostEqual(calculate_iou(b1, b2), 1.0)

        # Disjoint boxes -> IoU = 0.0
        b3 = BoundingBox(x=100, y=100, width=50, height=50)
        self.assertAlmostEqual(calculate_iou(b1, b3), 0.0)

        # Partial overlap
        b4 = BoundingBox(x=35, y=10, width=50, height=50)
        iou = calculate_iou(b1, b4)
        self.assertGreater(iou, 0.2)
        self.assertLess(iou, 0.5)

    def test_multi_frame_track_association(self):
        # Frame 0: detection at (100, 100)
        d0 = DetectionResult(
            bbox=BoundingBox(x=100, y=100, width=60, height=60),
            face_crop=np.zeros((60, 60, 3), dtype=np.uint8),
            quality=FaceQualityResult(
                is_usable=True, quality_score=0.8, blur_score=100, brightness_score=120, face_size_pixels=60
            ),
        )
        res0 = self.tracker.update(0, [d0])
        self.assertEqual(len(res0), 1)
        track_id_0 = res0[0][0]

        # Frame 1: slight shift to (105, 102) -> should associate to same track!
        d1 = DetectionResult(
            bbox=BoundingBox(x=105, y=102, width=60, height=60),
            face_crop=np.zeros((60, 60, 3), dtype=np.uint8),
            quality=FaceQualityResult(
                is_usable=True, quality_score=0.82, blur_score=110, brightness_score=120, face_size_pixels=60
            ),
        )
        res1 = self.tracker.update(1, [d1])
        self.assertEqual(len(res1), 1)
        track_id_1 = res1[0][0]
        self.assertEqual(track_id_0, track_id_1)

    def test_track_disappearance_and_timeout(self):
        d0 = DetectionResult(
            bbox=BoundingBox(x=50, y=50, width=60, height=60),
            face_crop=np.zeros((60, 60, 3), dtype=np.uint8),
            quality=FaceQualityResult(
                is_usable=True, quality_score=0.8, blur_score=100, brightness_score=120, face_size_pixels=60
            ),
        )
        res0 = self.tracker.update(0, [d0])
        tid = res0[0][0]
        self.assertIn(tid, self.tracker.active_tracks)

        # 4 consecutive empty frames -> exceeds max_missed_frames (3)
        for f in range(1, 5):
            self.tracker.update(f, [])

        self.assertNotIn(tid, self.tracker.active_tracks)

    def test_track_manager_averaging(self):
        # Add 3 observations with known embeddings
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        dummy_q = FaceQualityResult(
            is_usable=True, quality_score=0.9, blur_score=100, brightness_score=120, face_size_pixels=60
        )
        dummy_box = BoundingBox(x=10, y=10, width=50, height=50)

        self.manager.record("TRK_1", dummy_q, v1, dummy_box)
        self.manager.record("TRK_1", dummy_q, v2, dummy_box)

        evidence = self.manager.get_or_create("TRK_1")
        self.assertEqual(evidence.usable_observations_count, 2)

        mean_emb = evidence.get_representative_embedding()
        self.assertIsNotNone(mean_emb)
        # Normalized mean of [1,0,0] and [0,1,0] should have equal components and norm 1.0
        self.assertAlmostEqual(mean_emb[0], mean_emb[1], places=3)
        self.assertAlmostEqual(np.linalg.norm(mean_emb), 1.0, places=3)


if __name__ == "__main__":
    unittest.main()
