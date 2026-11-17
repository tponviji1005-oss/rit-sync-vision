"""
RIT-Sync Vision - Lighting & Exposure Quality Checker
Evaluates average luminance and extreme contrast to ensure reliable feature recognition.
"""

from typing import Tuple
import cv2
import numpy as np


class LightingChecker:
    def __init__(self, min_brightness: float = 40.0, max_brightness: float = 225.0):
        """
        :param min_brightness: Minimum mean luminance threshold (avoids underexposure/darkness)
        :param max_brightness: Maximum mean luminance threshold (avoids overexposure/washout)
        """
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness

    def evaluate(self, face_bgr: np.ndarray) -> Tuple[bool, float]:
        """
        :param face_bgr: Cropped face BGR image
        :return: (is_good_lighting, mean_luminance)
        """
        if face_bgr is None or face_bgr.size == 0:
            return False, 0.0

        if len(face_bgr.shape) == 3:
            gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_bgr

        mean_lum = float(np.mean(gray))
        is_good = (self.min_brightness <= mean_lum <= self.max_brightness)
        return is_good, mean_lum
