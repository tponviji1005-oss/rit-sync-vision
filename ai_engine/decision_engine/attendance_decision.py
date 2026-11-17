"""
RIT-Sync Vision - Attendance Decision Engine
Author: Paul Bryton Raj (AI & System Lead)

Converts multi-frame track evidence and open-set recognition into structured attendance suggestions.
Enforces the core institutional principle: NOT OBSERVED != ABSENT.
AI proposes; the teacher finalizes.
"""

from collections import Counter
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
        identity_consistency: float = 0.8,
    ):
        """
        :param identity_consistency: Minimum share of per-frame matches that must agree with the
            track's dominant identity. Below this, the track probably switched between people
            (tracker ID swap) and is flagged CONFLICTING_IDENTITY.
        """
        self.min_evidence_frames = min_evidence_frames
        self.identity_consistency = identity_consistency
        self.unknown_detector = UnknownDetector(
            similarity_threshold=similarity_threshold,
            margin_threshold=margin_threshold,
        )
        self.confidence_evaluator = ConfidenceEvaluator(min_evidence_frames=min_evidence_frames)
        self.duplicate_checker = DuplicateChecker(min_evidence_frames=min_evidence_frames)

    def _track_identity_is_consistent(
        self,
        track: TrackEvidence,
        enrolled_templates: List[EnrolledTemplate],
        model_version: Optional[str],
    ) -> bool:
        """Checks per-frame top-1 identities within a track for an identity switch."""
        if len(track.embeddings) < 2:
            return True
        ids = []
        for emb in track.embeddings:
            res = self.unknown_detector.identify(emb, enrolled_templates, model_version=model_version)
            if res.match_state == MatchState.MATCHED and res.student_id:
                ids.append(res.student_id)
        counts = Counter(ids)
        if len(counts) < 2:
            return True
        dominant = counts.most_common(1)[0][1]
        return dominant / float(len(ids)) >= self.identity_consistency

    def process_tracks(
        self,
        tracks: List[TrackEvidence],
        enrolled_templates: List[EnrolledTemplate],
        roster_student_ids: List[str],
        roster_names: Optional[Dict[str, str]] = None,
        model_version: Optional[str] = None,
    ) -> Tuple[List[AttendanceCandidate], List[Observation]]:
        """
        :param tracks: Consolidated track evidence from TrackManager
        :param enrolled_templates: List of enrolled templates for the class
        :param roster_student_ids: List of student IDs expected in the class
        :param roster_names: Optional mapping of student_id -> student_name
        :param model_version: Encoder model version; templates from other models are not compared
        :return: (candidates_list, track_observations_list)
        """
        if roster_names is None:
            roster_names = {t.student_id: t.student_name for t in enrolled_templates}
        roster_set = set(roster_student_ids)

        observations: List[Observation] = []
        observed_candidates: List[AttendanceCandidate] = []
        track_spans: Dict[str, Tuple[int, int]] = {}

        for track in tracks:
            if track.first_frame is not None and track.last_frame is not None:
                track_spans[track.track_id] = (track.first_frame, track.last_frame)

            rep_embedding = track.get_representative_embedding()
            rec_result: RecognitionResult = self.unknown_detector.identify(
                query_embedding=rep_embedding,
                enrolled_templates=enrolled_templates,
                model_version=model_version,
            )

            avg_quality = float(np.mean(track.quality_scores)) if track.quality_scores else 0.0

            composite_confidence = self.confidence_evaluator.calculate_confidence(
                match_similarity=rec_result.confidence,
                usable_frames=track.usable_observations_count,
                avg_quality_score=avg_quality,
            )

            reasons = list(rec_result.reason_codes)
            if rec_result.match_state == MatchState.INSUFFICIENT_QUALITY:
                # Explain *why* quality was insufficient
                for r in track.accumulated_reasons:
                    if r not in reasons:
                        reasons.append(r)
            if track.usable_observations_count < self.min_evidence_frames:
                if ReasonCode.INSUFFICIENT_EVIDENCE not in reasons:
                    reasons.append(ReasonCode.INSUFFICIENT_EVIDENCE)

            identity_consistent = True
            if rec_result.student_id:
                identity_consistent = self._track_identity_is_consistent(
                    track, enrolled_templates, model_version
                )
                if not identity_consistent and ReasonCode.CONFLICTING_IDENTITY not in reasons:
                    reasons.append(ReasonCode.CONFLICTING_IDENTITY)

            match_state = rec_result.match_state
            if match_state == MatchState.MATCHED and not identity_consistent:
                match_state = MatchState.NEEDS_REVIEW

            observations.append(
                Observation(
                    track_id=track.track_id,
                    candidate_student_id=rec_result.student_id,
                    match_state=match_state,
                    confidence=round(rec_result.confidence, 4),
                    reason_codes=reasons,
                    evidence_count=track.usable_observations_count,
                    total_observations=track.observations_count,
                    bbox=track.last_bbox,
                )
            )

            # Only enrolled roster students become attendance candidates
            if rec_result.student_id and rec_result.student_id in roster_set:
                s_id = rec_result.student_id
                s_name = roster_names.get(s_id, rec_result.student_name or s_id)

                if (
                    match_state == MatchState.MATCHED
                    and track.usable_observations_count >= self.min_evidence_frames
                ):
                    candidate_state = AttendanceCandidateState.PRESENT_CANDIDATE
                else:
                    candidate_state = AttendanceCandidateState.NEEDS_REVIEW

                observed_candidates.append(
                    AttendanceCandidate(
                        student_id=s_id,
                        student_name=s_name,
                        candidate_state=candidate_state,
                        confidence=composite_confidence,
                        reason_codes=reasons,
                        evidence_count=track.usable_observations_count,
                        matched_track_id=track.track_id,
                    )
                )

        # Reconcile duplicates: merge fragmented tracks, flag simultaneous conflicts
        reconciled_observed = self.duplicate_checker.reconcile(
            observed_candidates, track_spans=track_spans if track_spans else None
        )

        # Every roster student not observed: NOT_OBSERVED (never ABSENT)
        all_candidates: List[AttendanceCandidate] = list(reconciled_observed)
        reconciled_ids = {c.student_id for c in reconciled_observed}

        for s_id in roster_student_ids:
            if s_id not in reconciled_ids:
                all_candidates.append(
                    AttendanceCandidate(
                        student_id=s_id,
                        student_name=roster_names.get(s_id, s_id),
                        candidate_state=AttendanceCandidateState.NOT_OBSERVED,
                        confidence=0.0,
                        reason_codes=[],
                        evidence_count=0,
                        matched_track_id=None,
                    )
                )

        return all_candidates, observations
