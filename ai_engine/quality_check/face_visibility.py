"""
RIT-Sync Vision - Face Visibility & Geometry Checker
Evaluates minimum face size, aspect ratio, and boundary clipping.
"""

from typing import Tuple, List
from shared.constants import ReasonCode


class FaceVisibilityChecker:
    def __init__(
        self,
        min_size_pixels: int = 48,
        min_aspect_ratio: float = 0.65,
        max_aspect_ratio: float = 1.45,
    ):
        """
        :param min_size_pixels: Minimum acceptable width and height in pixels
        :param min_aspect_ratio: Minimum width/height ratio
        :param max_aspect_ratio: Maximum width/height ratio
        """
        self.min_size_pixels = min_size_pixels
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio

    def evaluate(
        self, x: int, y: int, w: int, h: int, frame_w: int, frame_h: int
    ) -> Tuple[bool, List[ReasonCode]]:
        """
        :return: (is_visible_and_valid, list_of_reason_codes)
        """
        reasons = []

        # Check minimum size
        if w < self.min_size_pixels or h < self.min_size_pixels:
            reasons.append(ReasonCode.FACE_TOO_SMALL)

        # Check aspect ratio
        if h > 0:
            aspect = w / float(h)
            if aspect < self.min_aspect_ratio or aspect > self.max_aspect_ratio:
                reasons.append(ReasonCode.FACE_ANGLE_UNSUITABLE)

        # Check frame boundary clipping (face cut off at edge of camera)
        margin = 4
        if x <= margin or y <= margin or (x + w) >= (frame_w - margin) or (y + h) >= (frame_h - margin):
            reasons.append(ReasonCode.FACE_OCCLUDED)

        return (len(reasons) == 0), reasons
