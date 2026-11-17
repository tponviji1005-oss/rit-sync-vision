"""
RIT-Sync Vision - Attendance Decision Engine
Author: Paul Bryton Raj (AI & System Lead)

Converts multi-frame track evidence and open-set recognition into structured attendance suggestions.
Enforces the core institutional principle: NOT OBSERVED != ABSENT.
AI proposes; the teacher finalizes.
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from shared.constants import (
    MatchState,
    AttendanceCandidateState,
    ReasonCode,
)
from shared.schemas import (
    AttendanceCandidate,
    Observation,
    EnrolledTemplate,
)
from ai_engine.tracking.track_manager import TrackEvidence
from ai_engine.recognition.unknown_detector import UnknownDetector, RecognitionResult
from ai_engine.decision_engine.confidence import ConfidenceEvaluator
from ai_engine.decision_engine.duplicate_checker import DuplicateChecker


class AttendanceDecisionEngine:
    """
    Synthesizes session track observations and class roster into structured proposals.
    """

    def __init__(
        self,
        min_evidence_frames: int = 3,
        similarity_threshold: float = 0.65,
        margin_threshold: float = 0.10,
    ):
        self.min_evidence_frames = min_evidence_frames
        self.unknown_detector = UnknownDetector(
            similarity_threshold=similarity_threshold,
            margin_threshold=margin_threshold,
        )
        self.confidence_evaluator = ConfidenceEvaluator(min_evidence_frames=min_evidence_frames)
        self.duplicate_checker = DuplicateChecker()

    def process_tracks(
        self,
        tracks: List[TrackEvidence],
        enrolled_templates: List[EnrolledTemplate],
        roster_student_ids: List[str],
        roster_names: Optional[Dict[str, str]] = None,
    ) -> Tuple[List[AttendanceCandidate], List[Observation]]:
        """
        :param tracks: Consolidated track evidence from TrackManager
        :param enrolled_templates: List of enrolled templates for the class
        :param roster_student_ids: List of student IDs expected in the class
        :param roster_names: Optional mapping of student_id -> student_name
        :return: (candidates_list, track_observations_list)
        """
        if roster_names is None:
            roster_names = {t.student_id: t.student_name for t in enrolled_templates}

        observations: List[Observation] = []
        observed_candidates: List[AttendanceCandidate] = []
        observed_student_ids = set()

        for track in tracks:
            rep_embedding = track.get_representative_embedding()
            rec_result: RecognitionResult = self.unknown_detector.identify(
                query_embedding=rep_embedding,
                enrolled_templates=enrolled_templates,
            )

            avg_quality = float(np.mean(track.quality_scores)) if track.quality_scores else 0.0

            # Compute composite confidence
            composite_confidence = self.confidence_evaluator.calculate_confidence(
                match_similarity=rec_result.confidence,
                usable_frames=track.usable_observations_count,
                avg_quality_score=avg_quality,
            )

            # Combine reason codes
            reasons = list(rec_result.reason_codes)
            if track.usable_observations_count < self.min_evidence_frames:
                if ReasonCode.INSUFFICIENT_EVIDENCE not in reasons:
                    reasons.append(ReasonCode.INSUFFICIENT_EVIDENCE)

            # Record track observation
            obs = Observation(
                track_id=track.track_id,
                candidate_student_id=rec_result.student_id,
                match_state=rec_result.match_state,
                confidence=round(rec_result.confidence, 4),
                reason_codes=reasons,
                evidence_count=track.usable_observations_count,
                bbox=track.last_bbox,
            )
            observations.append(obs)

            # If student recognized as an enrolled candidate
            if rec_result.student_id and rec_result.student_id in roster_student_ids:
                s_id = rec_result.student_id
                s_name = roster_names.get(s_id, rec_result.student_name or s_id)

                # Determine candidate state
                if (
                    rec_result.match_state == MatchState.MATCHED
                    and track.usable_observations_count >= self.min_evidence_frames
                ):
                    candidate_state = AttendanceCandidateState.PRESENT_CANDIDATE
                else:
                    candidate_state = AttendanceCandidateState.NEEDS_REVIEW

                cand = AttendanceCandidate(
                    student_id=s_id,
                    student_name=s_name,
                    candidate_state=candidate_state,
                    confidence=composite_confidence,
                    reason_codes=reasons,
                    evidence_count=track.usable_observations_count,
                    matched_track_id=track.track_id,
                )
                observed_candidates.append(cand)
                observed_student_ids.add(s_id)

        # Reconcile duplicates and track conflicts
        reconciled_observed = self.duplicate_checker.reconcile(observed_candidates)

        # For every student in roster NOT observed by camera: mark NOT_OBSERVED (Never ABSENT!)
        all_candidates: List[AttendanceCandidate] = list(reconciled_observed)
        reconciled_ids = {c.student_id for c in reconciled_observed}

        for s_id in roster_student_ids:
            if s_id not in reconciled_ids:
                s_name = roster_names.get(s_id, s_id)
                all_candidates.append(
                    AttendanceCandidate(
                        student_id=s_id,
                        student_name=s_name,
                        candidate_state=AttendanceCandidateState.NOT_OBSERVED,
                        confidence=0.0,
                        reason_codes=[],
                        evidence_count=0,
                        matched_track_id=None,
                    )
                )

        return all_candidates, observations
