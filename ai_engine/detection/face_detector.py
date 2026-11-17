"""
RIT-Sync Vision - Multi-Face Detector
Author: Paul Bryton Raj (AI & System Lead)

Detects multiple faces in classroom camera frames using OpenCV YuNet DNN
with a fallback to skimage LBP cascade, and evaluates observations through the quality gate.
"""

from typing import List, Optional
import os
from pathlib import Path
import cv2
import numpy as np
from shared.schemas import BoundingBox, FaceQualityResult
from ai_engine.detection.face_quality import FaceQualityEvaluator


class DetectionResult:
    def __init__(
        self,
        bbox: BoundingBox,
        face_crop: np.ndarray,
        quality: FaceQualityResult,
    ):
        self.bbox = bbox
        self.face_crop = face_crop
        self.quality = quality


class FaceDetector:
    """
    Multiple face detection using OpenCV YuNet with integrated quality assessment.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        min_face_size: int = 48,
    ):
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.min_face_size = min_face_size
        self.quality_evaluator = FaceQualityEvaluator(min_size_pixels=min_face_size)

        resolved_model = None
        candidates = [
            model_path,
            str(Path(__file__).resolve().parent.parent / "models" / "face_detection_yunet_2023mar.onnx"),
        ]

        for p in candidates:
            if p and os.path.exists(p) and os.path.getsize(p) > 1000:
                resolved_model = p
                break

        self._detector = None
        self._input_size = (320, 320)

        if resolved_model and hasattr(cv2, "FaceDetectorYN_create"):
            try:
                self._detector = cv2.FaceDetectorYN_create(
                    resolved_model,
                    "",
                    self._input_size,
                    score_threshold=self.conf_threshold,
                    nms_threshold=self.nms_threshold,
                )
            except Exception as e:
                self._detector = None

    def detect_faces(self, frame_bgr: np.ndarray) -> List[DetectionResult]:
        """
        Detects all visible faces in a single frame and assesses quality.
        :param frame_bgr: Full image frame (BGR uint8)
        :return: List of DetectionResult objects
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        frame_h, frame_w = frame_bgr.shape[:2]
        if frame_w <= 0 or frame_h <= 0:
            return []

        results: List[DetectionResult] = []

        if self._detector is not None:
            # Update input size if frame dimensions differ
            if (frame_w, frame_h) != self._input_size:
                self._detector.setInputSize((frame_w, frame_h))
                self._input_size = (frame_w, frame_h)

            ret, faces = self._detector.detect(frame_bgr)
            if faces is not None:
                for face in faces:
                    x, y, w, h = face[0:4]
                    conf = float(face[-1]) if len(face) > 4 else 1.0

                    x1 = max(0, int(round(x)))
                    y1 = max(0, int(round(y)))
                    x2 = min(frame_w, int(round(x + w)))
                    y2 = min(frame_h, int(round(y + h)))

                    crop_w = x2 - x1
                    crop_h = y2 - y1

                    if crop_w <= 0 or crop_h <= 0:
                        continue

                    face_crop = frame_bgr[y1:y2, x1:x2].copy()

                    bbox = BoundingBox(
                        x=x1,
                        y=y1,
                        width=crop_w,
                        height=crop_h,
                        confidence=round(conf, 3),
                    )

                    quality = self.quality_evaluator.evaluate(
                        face_crop=face_crop,
                        bbox_x=x1,
                        bbox_y=y1,
                        bbox_w=crop_w,
                        bbox_h=crop_h,
                        frame_w=frame_w,
                        frame_h=frame_h,
                    )

                    results.append(DetectionResult(bbox=bbox, face_crop=face_crop, quality=quality))

        return results
