"""
RIT-Sync Vision - Face Feature Encoder
Author: Paul Bryton Raj (AI & System Lead)

Generates normalized numerical face embeddings (128-d vectors) from face crops.
Quality gate is enforced: unusable face crops cannot be encoded.
"""

from typing import Optional, List
import cv2
import numpy as np
from shared.schemas import FaceQualityResult
from ai_engine.detection.face_quality import FaceQualityEvaluator


class FaceEncoder:
    """
    Extracts L2-normalized 128-dimensional feature representations for face verification.
    """

    def __init__(self, embedding_dim: int = 128, min_face_size: int = 48):
        self.embedding_dim = embedding_dim
        self.target_size = (112, 112)
        self.quality_evaluator = FaceQualityEvaluator(min_size_pixels=min_face_size)

    def encode(
        self, face_crop: np.ndarray, enforce_quality: bool = True
    ) -> Optional[List[float]]:
        """
        Extracts an L2-normalized 128-dimensional embedding from a face image.
        :param face_crop: Cropped face image (BGR)
        :param enforce_quality: If True, rejects blurry or low-quality crops
        :return: 128-length list of floats, or None if quality fails
        """
        if face_crop is None or face_crop.size == 0:
            return None

        h, w = face_crop.shape[:2]
        if w < 16 or h < 16:
            return None

        if enforce_quality:
            quality: FaceQualityResult = self.quality_evaluator.evaluate(
                face_crop=face_crop,
                bbox_x=0,
                bbox_y=0,
                bbox_w=w,
                bbox_h=h,
                frame_w=w + 20,
                frame_h=h + 20,
            )
            if not quality.is_usable:
                return None

        # Standardize face crop to 112x112
        resized = cv2.resize(face_crop, self.target_size, interpolation=cv2.INTER_AREA)

        # Convert to grayscale and equalize
        if len(resized.shape) == 3:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = resized

        equalized = cv2.equalizeHist(gray)

        # Multi-scale spatial gradient feature extraction
        # Compute horizontal and vertical Sobel gradients
        gx = cv2.Sobel(equalized, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(equalized, cv2.CV_32F, 0, 1, ksize=3)

        mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)

        # Partition into an 4x4 spatial grid (16 cells)
        cell_h = self.target_size[1] // 4
        cell_w = self.target_size[0] // 4
        num_bins = 8  # 8 orientation bins per cell -> 16 * 8 = 128 dimensions!

        hist_features = []
        for i in range(4):
            for j in range(4):
                cell_mag = mag[i * cell_h : (i + 1) * cell_h, j * cell_w : (j + 1) * cell_w]
                cell_ang = ang[i * cell_h : (i + 1) * cell_h, j * cell_w : (j + 1) * cell_w]

                # Bin orientations into 8 bins (each 45 degrees)
                bins = (cell_ang / 45.0).astype(int) % num_bins
                cell_hist = np.zeros(num_bins, dtype=np.float32)
                for b in range(num_bins):
                    cell_hist[b] = np.sum(cell_mag[bins == b])

                # Cell normalization
                cell_norm = np.linalg.norm(cell_hist) + 1e-6
                hist_features.extend(cell_hist / cell_norm)

        vector = np.array(hist_features, dtype=np.float32)

        # Global L2 normalization
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return [round(float(v), 6) for v in vector]
