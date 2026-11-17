"""
RIT-Sync Vision - Face Quality Evaluator
Aggregates individual checks (blur, lighting, visibility) into a consolidated quality decision.
"""

from typing import List
import numpy as np
from shared.constants import ReasonCode
from shared.schemas import FaceQualityResult
from ai_engine.quality_check.blur_check import BlurChecker
from ai_engine.quality_check.lighting_check import LightingChecker
from ai_engine.quality_check.face_visibility import FaceVisibilityChecker


class FaceQualityEvaluator:
    def __init__(
        self,
        blur_threshold: float = 80.0,
        min_brightness: float = 40.0,
        max_brightness: float = 225.0,
        min_size_pixels: int = 48,
    ):
        self.blur_checker = BlurChecker(blur_threshold=blur_threshold)
        self.lighting_checker = LightingChecker(min_brightness=min_brightness, max_brightness=max_brightness)
        self.visibility_checker = FaceVisibilityChecker(min_size_pixels=min_size_pixels)

    def evaluate(
        self,
        face_crop: np.ndarray,
        bbox_x: int,
        bbox_y: int,
        bbox_w: int,
        bbox_h: int,
        frame_w: int,
        frame_h: int,
    ) -> FaceQualityResult:
        """
        Evaluates the face observation against all quality gates.
        """
        reason_codes: List[ReasonCode] = []

        # 1. Visibility & Geometry Check
        vis_ok, vis_reasons = self.visibility_checker.evaluate(
            bbox_x, bbox_y, bbox_w, bbox_h, frame_w, frame_h
        )
        reason_codes.extend(vis_reasons)

        # 2. Blur Check
        is_sharp, blur_val = self.blur_checker.evaluate(face_crop)
        if not is_sharp:
            reason_codes.append(ReasonCode.IMAGE_BLUR)

        # 3. Lighting Check
        good_light, lum_val = self.lighting_checker.evaluate(face_crop)
        if not good_light:
            reason_codes.append(ReasonCode.POOR_LIGHTING)

        # Compute normalized quality score (0.0 to 1.0)
        # Quality penalizes for blur, bad lighting, and small size
        blur_factor = min(1.0, blur_val / 200.0)
        lum_factor = 1.0 - abs(lum_val - 128.0) / 128.0
        lum_factor = max(0.0, min(1.0, lum_factor))
        size_factor = min(1.0, min(bbox_w, bbox_h) / 120.0)

        quality_score = float(0.4 * blur_factor + 0.3 * lum_factor + 0.3 * size_factor)

        # If any hard check fails, mark is_usable = False
        is_usable = (len(reason_codes) == 0) and (quality_score >= 0.40)
        if not is_usable and ReasonCode.INSUFFICIENT_QUALITY not in reason_codes:
            reason_codes.append(ReasonCode.INSUFFICIENT_QUALITY)

        min_dim = min(bbox_w, bbox_h)

        return FaceQualityResult(
            is_usable=is_usable,
            quality_score=round(quality_score, 3),
            blur_score=round(blur_val, 2),
            brightness_score=round(lum_val, 2),
            face_size_pixels=min_dim,
            reason_codes=reason_codes,
        )
