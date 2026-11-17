"""
RIT-Sync Vision - Duplicate & Conflict Reconciler
Author: Paul Bryton Raj (AI & System Lead)

Reconciles multiple tracks that resolved to the same enrolled student:

1. Fragmentation: the tracks never overlap in time (the person was lost and re-acquired by the
   tracker). The tracks are merged into one candidate; evidence is summed and no conflict is raised.
   DUPLICATE_CANDIDATE is still attached so the merge is visible to the teacher.
2. Conflict: two tracks were visible in the SAME frames yet both match one student. One physical
   person cannot be in two places, so at least one match is wrong. The candidate is routed to
   NEEDS_REVIEW with DUPLICATE_CANDIDATE + CONFLICTING_IDENTITY.

Either way, one session yields at most one candidate per student.
"""

from typing import Dict, List, Optional, Tuple
from shared.constants import AttendanceCandidateState, ReasonCode
from shared.schemas import AttendanceCandidate

# Reasons that, on any merged part, require teacher review regardless of evidence count.
_REVIEW_REASONS = {
    ReasonCode.AMBIGUOUS_MATCH,
    ReasonCode.CONFLICTING_IDENTITY,
    ReasonCode.LOW_MATCH_CONFIDENCE,
    ReasonCode.MODEL_VERSION_MISMATCH,
}


class DuplicateChecker:
    """
    Reconciles track-level candidate matches against student identities to prevent duplicates.
    """

    def __init__(self, min_evidence_frames: int = 3):
        self.min_evidence_frames = min_evidence_frames

    @staticmethod
    def _any_overlap(spans: List[Optional[Tuple[int, int]]]) -> bool:
        if any(s is None for s in spans):
            return True  # Unknown timing: be conservative
        ordered = sorted(spans)
        for (_, prev_end), (next_start, _) in zip(ordered, ordered[1:]):
            if next_start <= prev_end:
                return True
        return False

    def reconcile(
        self,
        candidates: List[AttendanceCandidate],
        track_spans: Optional[Dict[str, Tuple[int, int]]] = None,
    ) -> List[AttendanceCandidate]:
        """
        :param candidates: Track-level candidates (possibly several per student)
        :param track_spans: track_id -> (first_frame, last_frame). Without it, every duplicate
                            is treated as a conflict (conservative behaviour).
        """
        student_map: Dict[str, List[AttendanceCandidate]] = {}
        for cand in candidates:
            student_map.setdefault(cand.student_id, []).append(cand)

        reconciled: List[AttendanceCandidate] = []

        for student_id, cand_list in student_map.items():
            if len(cand_list) == 1:
                reconciled.append(cand_list[0])
                continue

            best_cand = max(cand_list, key=lambda c: c.confidence)
            all_tracks = [c.matched_track_id for c in cand_list if c.matched_track_id]
            total_evidence = sum(c.evidence_count for c in cand_list)

            spans = [(track_spans or {}).get(c.matched_track_id) for c in cand_list]
            is_conflict = track_spans is None or self._any_overlap(spans)

            reasons: List[ReasonCode] = []
            for c in cand_list:
                for r in c.reason_codes:
                    if r not in reasons:
                        reasons.append(r)
            if ReasonCode.DUPLICATE_CANDIDATE not in reasons:
                reasons.append(ReasonCode.DUPLICATE_CANDIDATE)

            if is_conflict:
                if ReasonCode.CONFLICTING_IDENTITY not in reasons:
                    reasons.append(ReasonCode.CONFLICTING_IDENTITY)
                state = AttendanceCandidateState.NEEDS_REVIEW
            else:
                # Fragmented track of one person: pooled evidence may now be sufficient.
                if total_evidence >= self.min_evidence_frames and ReasonCode.INSUFFICIENT_EVIDENCE in reasons:
                    reasons.remove(ReasonCode.INSUFFICIENT_EVIDENCE)
                needs_review = (
                    total_evidence < self.min_evidence_frames
                    or any(r in _REVIEW_REASONS for r in reasons)
                    or any(
                        c.candidate_state == AttendanceCandidateState.NEEDS_REVIEW
                        and ReasonCode.INSUFFICIENT_EVIDENCE not in c.reason_codes
                        for c in cand_list
                    )
                )
                state = (
                    AttendanceCandidateState.NEEDS_REVIEW
                    if needs_review
                    else AttendanceCandidateState.PRESENT_CANDIDATE
                )

            reconciled.append(
                AttendanceCandidate(
                    student_id=student_id,
                    student_name=best_cand.student_name,
                    candidate_state=state,
                    confidence=best_cand.confidence,
                    reason_codes=reasons,
                    evidence_count=total_evidence,
                    matched_track_id=",".join(filter(None, all_tracks)),
                )
            )

        return reconciled
