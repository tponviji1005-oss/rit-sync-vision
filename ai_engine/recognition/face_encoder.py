"""
RIT-Sync Vision - Face Feature Encoder
Author: Paul Bryton Raj (AI & System Lead)

Generates L2-normalized 128-d face embeddings.

Backends (selected automatically, in order):
1. "sface_2021dec"  - OpenCV SFace recognition model (Apache-2.0). Requires
                      ai_engine/models/face_recognition_sface_2021dec.onnx
                      (fetch with scripts/download_models.py). Uses YuNet landmarks for alignment.
2. "gradient_v1"    - Hand-crafted gradient-orientation histogram. Deterministic and dependency-free,
                      but it is NOT an identity-discriminative face recognition model. It exists for
                      tests and offline development only; never report recognition accuracy with it.

Every template stores the `model_version` that produced it. Embeddings from different backends
are not comparable, so matching rejects templates whose model_version differs.
"""

from typing import Optional, List, Dict
import os
import logging
from pathlib import Path
import cv2
import numpy as np
from shared.schemas import FaceQualityResult
from ai_engine.detection.face_quality import FaceQualityEvaluator

logger = logging.getLogger("rit_sync_vision.face_encoder")

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
SFACE_MODEL = "face_recognition_sface_2021dec.onnx"

BACKEND_SFACE = "sface_2021dec"
BACKEND_GRADIENT = "gradient_v1"

# Default open-set thresholds per backend (cosine similarity).
# SFace: 0.363 is the published 1:1 cosine threshold from the OpenCV zoo (LFW). It must be
# re-calibrated on project validation data (see scripts/evaluate_ai.py).
# Gradient baseline: arbitrary; only meaningful for synthetic tests.
RECOMMENDED_THRESHOLDS: Dict[str, Dict[str, float]] = {
    BACKEND_SFACE: {"similarity_threshold": 0.363, "margin_threshold": 0.08},
    BACKEND_GRADIENT: {"similarity_threshold": 0.65, "margin_threshold": 0.10},
}


class FaceEncoder:
    """
    Extracts L2-normalized 128-dimensional feature representations for open-set matching.
    """

    def __init__(
        self,
        embedding_dim: int = 128,
        min_face_size: int = 48,
        backend: str = "auto",
        sface_model_path: Optional[str] = None,
    ):
        """
        :param backend: "auto" (SFace if available, else gradient), "sface" or "gradient"
        """
        self.embedding_dim = embedding_dim
        self.target_size = (112, 112)
        self.quality_evaluator = FaceQualityEvaluator(min_size_pixels=min_face_size)
        self._sface = None

        if backend in ("auto", "sface"):
            path = sface_model_path or str(MODELS_DIR / SFACE_MODEL)
            if os.path.exists(path) and hasattr(cv2, "FaceRecognizerSF"):
                try:
                    self._sface = cv2.FaceRecognizerSF.create(path, "")
                except Exception as e:
                    logger.warning("SFace model failed to load (%s).", type(e).__name__)
                    self._sface = None
            if backend == "sface" and self._sface is None:
                raise RuntimeError(
                    "SFace backend requested but model is unavailable. Run scripts/download_models.py."
                )

        self.backend_name = BACKEND_SFACE if self._sface is not None else BACKEND_GRADIENT
        if self.backend_name == BACKEND_GRADIENT and backend == "auto":
            logger.warning(
                "SFace model not found; using gradient_v1 development encoder. "
                "Recognition results are NOT meaningful for real faces."
            )

    @property
    def model_version(self) -> str:
        return self.backend_name

    @property
    def is_identity_model(self) -> bool:
        """True only for a real face recognition model."""
        return self.backend_name == BACKEND_SFACE

    @property
    def recommended_thresholds(self) -> Dict[str, float]:
        return dict(RECOMMENDED_THRESHOLDS[self.backend_name])

    def _quality_ok(self, face_crop: np.ndarray) -> bool:
        h, w = face_crop.shape[:2]
        # Place the crop inside a padded virtual frame so the edge-clipping check does not fire.
        pad = 10
        quality: FaceQualityResult = self.quality_evaluator.evaluate(
            face_crop=face_crop,
            bbox_x=pad,
            bbox_y=pad,
            bbox_w=w,
            bbox_h=h,
            frame_w=w + 2 * pad,
            frame_h=h + 2 * pad,
        )
        return quality.is_usable

    def encode(
        self,
        face_crop: np.ndarray,
        enforce_quality: bool = True,
        source_frame: Optional[np.ndarray] = None,
        face_row: Optional[np.ndarray] = None,
    ) -> Optional[List[float]]:
        """
        Extracts an L2-normalized 128-dimensional embedding from a face image.
        :param face_crop: Cropped face image (BGR)
        :param enforce_quality: If True, rejects blurry or low-quality crops
        :param source_frame: Full frame (enables landmark alignment with SFace)
        :param face_row: YuNet detection row for this face (enables alignment)
        :return: list of floats, or None if the crop is unusable
        """
        if face_crop is None or face_crop.size == 0:
            return None

        h, w = face_crop.shape[:2]
        if w < 16 or h < 16:
            return None

        if enforce_quality and not self._quality_ok(face_crop):
            return None

        if self._sface is not None:
            vector = self._encode_sface(face_crop, source_frame, face_row)
        else:
            vector = self._encode_gradient(face_crop)

        if vector is None:
            return None

        norm = np.linalg.norm(vector)
        if norm <= 0:
            return None
        vector = vector / norm
        return [round(float(v), 6) for v in vector]

    def _encode_sface(
        self,
        face_crop: np.ndarray,
        source_frame: Optional[np.ndarray],
        face_row: Optional[np.ndarray],
    ) -> Optional[np.ndarray]:
        try:
            if source_frame is not None and face_row is not None:
                aligned = self._sface.alignCrop(source_frame, face_row)
            else:
                # No landmarks (Haar fallback / enrollment crop): resize without alignment.
                aligned = cv2.resize(face_crop, self.target_size, interpolation=cv2.INTER_AREA)
            if aligned.ndim == 2:
                aligned = cv2.cvtColor(aligned, cv2.COLOR_GRAY2BGR)
            feat = self._sface.feature(aligned)
            return np.asarray(feat, dtype=np.float32).flatten()
        except Exception as e:
            logger.warning("SFace feature extraction failed (%s).", type(e).__name__)
            return None

    def _encode_gradient(self, face_crop: np.ndarray) -> np.ndarray:
        """Development-only gradient orientation histogram (4x4 cells x 8 bins = 128-d)."""
        resized = cv2.resize(face_crop, self.target_size, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if resized.ndim == 3 else resized
        equalized = cv2.equalizeHist(gray)

        gx = cv2.Sobel(equalized, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(equalized, cv2.CV_32F, 0, 1, ksize=3)
        mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)

        cell_h = self.target_size[1] // 4
        cell_w = self.target_size[0] // 4
        num_bins = 8

        hist_features = []
        for i in range(4):
            for j in range(4):
                cell_mag = mag[i * cell_h : (i + 1) * cell_h, j * cell_w : (j + 1) * cell_w]
                cell_ang = ang[i * cell_h : (i + 1) * cell_h, j * cell_w : (j + 1) * cell_w]
                bins = (cell_ang / 45.0).astype(int) % num_bins
                cell_hist = np.bincount(
                    bins.ravel(), weights=cell_mag.ravel(), minlength=num_bins
                ).astype(np.float32)
                cell_hist /= np.linalg.norm(cell_hist) + 1e-6
                hist_features.extend(cell_hist)

        return np.array(hist_features, dtype=np.float32)
