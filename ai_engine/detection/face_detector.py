"""
RIT-Sync Vision - Multi-Face Detector
Author: Paul Bryton Raj (AI & System Lead)

Detects multiple faces in classroom camera frames using OpenCV YuNet (DNN) with a fallback to
the OpenCV Haar frontal-face cascade, and evaluates every observation through the quality gate.

YuNet also returns 5 facial landmarks, which the recognition encoder uses for face alignment.
The Haar fallback returns no landmarks, so recognition falls back to an unaligned crop.
"""

from typing import List, Optional
import os
import logging
from pathlib import Path
import cv2
import numpy as np
from shared.schemas import BoundingBox, FaceQualityResult
from ai_engine.detection.face_quality import FaceQualityEvaluator

logger = logging.getLogger("rit_sync_vision.face_detector")

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
YUNET_MODEL = "face_detection_yunet_2023mar.onnx"
HAAR_MODEL = "haarcascade_frontalface_default.xml"

# Confidence reported for Haar detections, which have no calibrated score.
HAAR_NOMINAL_CONFIDENCE = 0.5


class DetectionResult:
    def __init__(
        self,
        bbox: BoundingBox,
        face_crop: np.ndarray,
        quality: FaceQualityResult,
        face_row: Optional[np.ndarray] = None,
        source_frame: Optional[np.ndarray] = None,
    ):
        """
        :param face_row: Raw YuNet output row (bbox + 5 landmarks + score) in full-frame coordinates,
                         used for alignment by the SFace encoder. None for Haar detections.
        :param source_frame: Reference to the full frame (in memory only, for aligned encoding).
                             Released by the pipeline once the frame has been processed.
        """
        self.bbox = bbox
        self.face_crop = face_crop
        self.quality = quality
        self.face_row = face_row
        self.source_frame = source_frame

    def release(self):
        """Drop image references so frame memory can be reclaimed (privacy)."""
        self.face_crop = None
        self.source_frame = None


class FaceDetector:
    """
    Multiple face detection using OpenCV YuNet, with Haar cascade fallback,
    and integrated quality assessment.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        min_face_size: int = 48,
        haar_path: Optional[str] = None,
    ):
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.min_face_size = min_face_size
        self.quality_evaluator = FaceQualityEvaluator(min_size_pixels=min_face_size)

        self._detector = None
        self._haar: Optional[cv2.CascadeClassifier] = None
        self._input_size = (320, 320)
        self.backend_name = "none"

        resolved_model = None
        for p in [model_path, str(MODELS_DIR / YUNET_MODEL)]:
            if p and os.path.exists(p) and os.path.getsize(p) > 1000:
                resolved_model = p
                break

        if resolved_model and hasattr(cv2, "FaceDetectorYN_create"):
            try:
                self._detector = cv2.FaceDetectorYN_create(
                    resolved_model,
                    "",
                    self._input_size,
                    score_threshold=self.conf_threshold,
                    nms_threshold=self.nms_threshold,
                )
                self.backend_name = "yunet_2023mar"
            except Exception as e:
                logger.warning("YuNet failed to load (%s); trying Haar fallback.", type(e).__name__)
                self._detector = None

        self._lbp = None
        if self._detector is None:
            haar_file = haar_path or str(MODELS_DIR / HAAR_MODEL)
            # OpenCV 4.x ships CascadeClassifier; OpenCV 5 moved it to opencv-contrib.
            if os.path.exists(haar_file) and hasattr(cv2, "CascadeClassifier"):
                cascade = cv2.CascadeClassifier(haar_file)
                if not cascade.empty():
                    self._haar = cascade
                    self.backend_name = "haar_frontalface_default"
            if self._haar is None:
                self._lbp = self._load_skimage_lbp()
                if self._lbp is not None:
                    self.backend_name = "skimage_lbp_frontal_face"
            if self._haar is None and self._lbp is None:
                logger.error("No face detection model could be loaded.")

    @staticmethod
    def _load_skimage_lbp():
        try:
            from skimage.feature import Cascade
            from skimage.data import lbp_frontal_face_cascade_filename
            return Cascade(lbp_frontal_face_cascade_filename())
        except Exception:
            return None

    @property
    def is_ready(self) -> bool:
        return self._detector is not None or self._haar is not None or self._lbp is not None

    @property
    def supports_landmarks(self) -> bool:
        return self._detector is not None

    def _raw_detections(self, frame_bgr: np.ndarray):
        """Returns list of (x, y, w, h, conf, face_row_or_None) in frame coordinates."""
        frame_h, frame_w = frame_bgr.shape[:2]
        raw = []

        if self._detector is not None:
            if (frame_w, frame_h) != self._input_size:
                self._detector.setInputSize((frame_w, frame_h))
                self._input_size = (frame_w, frame_h)
            _, faces = self._detector.detect(frame_bgr)
            if faces is not None:
                for face in faces:
                    x, y, w, h = face[0:4]
                    conf = float(face[-1]) if len(face) > 4 else 1.0
                    raw.append((x, y, w, h, conf, face.copy()))
        elif self._haar is not None:
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY) if frame_bgr.ndim == 3 else frame_bgr
            boxes = self._haar.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24)
            )
            for (x, y, w, h) in boxes:
                raw.append((float(x), float(y), float(w), float(h), HAAR_NOMINAL_CONFIDENCE, None))
        elif self._lbp is not None:
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY) if frame_bgr.ndim == 3 else frame_bgr
            boxes = self._lbp.detect_multi_scale(
                img=gray.astype(np.float32) / 255.0,
                scale_factor=1.2,
                step_ratio=1,
                min_size=(24, 24),
                max_size=(frame_w, frame_h),
            )
            for b in boxes:
                raw.append(
                    (float(b["c"]), float(b["r"]), float(b["width"]), float(b["height"]),
                     HAAR_NOMINAL_CONFIDENCE, None)
                )

        return raw

    def detect_faces(self, frame_bgr: np.ndarray) -> List[DetectionResult]:
        """
        Detects all visible faces in a single frame and assesses quality.
        :param frame_bgr: Full image frame (BGR uint8)
        :return: List of DetectionResult objects (empty if no faces or no model)
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        frame_h, frame_w = frame_bgr.shape[:2]
        if frame_w <= 0 or frame_h <= 0:
            return []

        results: List[DetectionResult] = []

        for x, y, w, h, conf, face_row in self._raw_detections(frame_bgr):
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
                confidence=round(max(0.0, min(1.0, conf)), 3),
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

            results.append(
                DetectionResult(
                    bbox=bbox,
                    face_crop=face_crop,
                    quality=quality,
                    face_row=face_row,
                    source_frame=frame_bgr,
                )
            )

        return results
