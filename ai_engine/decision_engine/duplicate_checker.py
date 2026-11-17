"""
RIT-Sync Vision - Duplicate & Conflict Reconciler
Author: Paul Bryton Raj (AI & System Lead)

Detects and resolves candidate conflicts:
1. Multiple tracks mapping to the same enrolled student.
2. Flags DUPLICATE_CANDIDATE and CONFLICTING_IDENTITY.
3. Automatically routes conflicting cases to teacher review (NEEDS_REVIEW).
"""

from typing import Dict, List, Set, Tuple
from shared.constants import AttendanceCandidateState, ReasonCode
from shared.schemas import AttendanceCandidate


class DuplicateChecker:
    """
    Reconciles track-level candidate matches against student identities to prevent duplicates.
    """

    def reconcile(
        self, candidates: List[AttendanceCandidate]
    ) -> List[AttendanceCandidate]:
        """
        Scans proposed candidates. If multiple tracks proposed the same student_id,
        merges their evidence, flags DUPLICATE_CANDIDATE / CONFLICTING_IDENTITY,
        and sets candidate_state = NEEDS_REVIEW.
        """
        student_map: Dict[str, List[AttendanceCandidate]] = {}

        for cand in candidates:
            if cand.student_id not in student_map:
                student_map[cand.student_id] = []
            student_map[cand.student_id].append(cand)

        reconciled: List[AttendanceCandidate] = []

        for student_id, cand_list in student_map.items():
            if len(cand_list) == 1:
                reconciled.append(cand_list[0])
            else:
                # Conflict: more than one track claimed this student!
                best_cand = max(cand_list, key=lambda c: c.confidence)
                all_tracks = [c.matched_track_id for c in cand_list if c.matched_track_id]
                total_evidence = sum(c.evidence_count for c in cand_list)

                reasons = list(best_cand.reason_codes)
                if ReasonCode.DUPLICATE_CANDIDATE not in reasons:
                    reasons.append(ReasonCode.DUPLICATE_CANDIDATE)
                if ReasonCode.CONFLICTING_IDENTITY not in reasons:
                    reasons.append(ReasonCode.CONFLICTING_IDENTITY)

                merged_candidate = AttendanceCandidate(
                    student_id=student_id,
                    student_name=best_cand.student_name,
                    candidate_state=AttendanceCandidateState.NEEDS_REVIEW,  # Must be teacher reviewed
                    confidence=best_cand.confidence,
                    reason_codes=reasons,
                    evidence_count=total_evidence,
                    matched_track_id=",".join(filter(None, all_tracks)),
                )
                reconciled.append(merged_candidate)

        return reconciled
