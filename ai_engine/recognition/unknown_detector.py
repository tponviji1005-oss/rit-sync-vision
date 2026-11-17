"""
RIT-Sync Vision - Open-Set UNKNOWN Detector
Author: Paul Bryton Raj (AI & System Lead)

Enforces open-set recognition principles:
1. Rejects nearest-match if similarity is below confidence threshold -> UNKNOWN.
2. Flags ambiguous ties (margin between 1st and 2nd best < margin threshold) -> NEEDS_REVIEW.
3. Distinguishes known enrolled students from unknown/unregistered visitors.
"""

from typing import List, Optional, Tuple
from shared.constants import MatchState, ReasonCode
from shared.schemas import EnrolledTemplate
from ai_engine.recognition.face_matcher import FaceMatcher, MatchCandidate


class RecognitionResult:
    def __init__(
        self,
        match_state: MatchState,
        student_id: Optional[str],
        student_name: Optional[str],
        confidence: float,
        reason_codes: List[ReasonCode],
        second_best_student_id: Optional[str] = None,
        second_best_similarity: Optional[float] = None,
    ):
        self.match_state = match_state
        self.student_id = student_id
        self.student_name = student_name
        self.confidence = confidence
        self.reason_codes = reason_codes
        self.second_best_student_id = second_best_student_id
        self.second_best_similarity = second_best_similarity


class UnknownDetector:
    """
    Open-set 1:N classifier with margin and threshold validation.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.65,
        margin_threshold: float = 0.10,
    ):
        """
        :param similarity_threshold: Minimum similarity to be considered a match
        :param margin_threshold: Minimum difference required between #1 and #2 matches
        """
        self.similarity_threshold = similarity_threshold
        self.margin_threshold = margin_threshold
        self.matcher = FaceMatcher()

    def identify(
        self,
        query_embedding: Optional[List[float]],
        enrolled_templates: List[EnrolledTemplate],
    ) -> RecognitionResult:
        """
        Runs open-set identification against enrolled templates.
        """
        if not query_embedding:
            return RecognitionResult(
                match_state=MatchState.INSUFFICIENT_QUALITY,
                student_id=None,
                student_name=None,
                confidence=0.0,
                reason_codes=[ReasonCode.INSUFFICIENT_QUALITY],
            )

        if not enrolled_templates:
            return RecognitionResult(
                match_state=MatchState.UNKNOWN,
                student_id=None,
                student_name=None,
                confidence=0.0,
                reason_codes=[ReasonCode.UNENROLLED_INDIVIDUAL],
            )

        top_matches: List[MatchCandidate] = self.matcher.find_top_matches(
            query_embedding, enrolled_templates, top_k=2
        )

        if not top_matches:
            return RecognitionResult(
                match_state=MatchState.UNKNOWN,
                student_id=None,
                student_name=None,
                confidence=0.0,
                reason_codes=[ReasonCode.LOW_MATCH_CONFIDENCE],
            )

        best = top_matches[0]
        second_best = top_matches[1] if len(top_matches) > 1 else None

        second_id = second_best.student_id if second_best else None
        second_sim = second_best.similarity if second_best else 0.0

        # Check 1: Similarity Threshold
        if best.similarity < self.similarity_threshold:
            return RecognitionResult(
                match_state=MatchState.UNKNOWN,
                student_id=None,
                student_name=None,
                confidence=best.similarity,
                reason_codes=[ReasonCode.LOW_MATCH_CONFIDENCE],
                second_best_student_id=second_id,
                second_best_similarity=second_sim,
            )

        # Check 2: Best vs Second-Best Margin Check (prevent ambiguous false matching)
        if second_best is not None:
            margin = best.similarity - second_best.similarity
            if margin < self.margin_threshold:
                # Ambiguous tie: close call between two enrolled students!
                return RecognitionResult(
                    match_state=MatchState.NEEDS_REVIEW,
                    student_id=best.student_id,
                    student_name=best.student_name,
                    confidence=best.similarity,
                    reason_codes=[ReasonCode.AMBIGUOUS_MATCH],
                    second_best_student_id=second_id,
                    second_best_similarity=second_sim,
                )

        # Clean, verified match
        return RecognitionResult(
            match_state=MatchState.MATCHED,
            student_id=best.student_id,
            student_name=best.student_name,
            confidence=best.similarity,
            reason_codes=[],
            second_best_student_id=second_id,
            second_best_similarity=second_sim,
        )
