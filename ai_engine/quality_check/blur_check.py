"""
RIT-Sync Vision - Blur Quality Checker
Computes Laplacian variance to detect blurred or out-of-focus face images.
"""

from typing import Tuple
import cv2
import numpy as np


class BlurChecker:
    def __init__(self, blur_threshold: float = 80.0):
        """
        :param blur_threshold: Laplacian variance threshold below which an image is considered blurry.
        """
        self.blur_threshold = blur_threshold

    def evaluate(self, face_bgr: np.ndarray) -> Tuple[bool, float]:
        """
        :param face_bgr: Cropped face BGR image
        :return: (is_sharp, blur_score)
        """
        if face_bgr is None or face_bgr.size == 0:
            return False, 0.0

        if len(face_bgr.shape) == 3:
            gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_bgr

        # Compute variance of Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = float(laplacian.var())
        is_sharp = variance >= self.blur_threshold
        return is_sharp, variance
