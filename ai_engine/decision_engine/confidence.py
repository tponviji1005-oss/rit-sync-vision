"""
RIT-Sync Vision - Confidence Evaluator
Author: Paul Bryton Raj (AI & System Lead)

Calculates aggregated confidence by combining:
1. Feature match similarity
2. Number of supporting frame observations (temporal persistence)
3. Quality scores across observed frames
"""

import numpy as np


class ConfidenceEvaluator:
    def __init__(self, min_evidence_frames: int = 3):
        self.min_evidence_frames = min_evidence_frames

    def calculate_confidence(
        self,
        match_similarity: float,
        usable_frames: int,
        avg_quality_score: float,
    ) -> float:
        """
        Computes composite confidence in range [0.0, 1.0].
        """
        if usable_frames <= 0:
            return 0.0

        # Evidence count factor: scales from 0.5 (1 frame) to 1.0 (>= min_evidence_frames)
        evidence_factor = min(1.0, 0.5 + 0.5 * (usable_frames / float(self.min_evidence_frames)))

        # Weighted combination: 60% match similarity, 25% evidence factor, 15% quality
        composite = (
            0.60 * match_similarity +
            0.25 * evidence_factor +
            0.15 * avg_quality_score
        )

        return round(float(np.clip(composite, 0.0, 1.0)), 4)
