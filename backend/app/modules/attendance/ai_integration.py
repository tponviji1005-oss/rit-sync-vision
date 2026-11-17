"""
RIT Sync Vision - AI Observation Integration Boundary
Authoritative backend integration for incoming AI observation payloads as defined in MANAGE.md §5 & §6.

Core Responsibilities:
1. Ingest and validate AI observation payloads against MANAGE.md §5 contract.
2. Enforce security: validate capture permit tokens (signature, hash, revocation, expiry, session & classroom matching).
3. Safely map AI match states to attendance candidate states:
   - MATCHED with confidence >= 0.70 -> PRESENT_CANDIDATE
   - MATCHED with confidence < 0.70 -> NEEDS_REVIEW (uncertain evidence)
   - NEEDS_REVIEW or INSUFFICIENT_QUALITY -> NEEDS_REVIEW
   - UNKNOWN -> Ignored (not assigned to identity)
4. Protect teacher-finalized records (AI observations NEVER overwrite teacher decisions).
5. Safeguard NOT_OBSERVED (unobserved students NEVER automatically become ABSENT).
6. Handle unknown student identifiers safely without crashing or leaking details.
7. Merge and deduplicate multiple tracks/observations within the same session/batch.
8. Privacy: Never accept, store, or log raw images, video frames, or biometric templates.
"""

import enum
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status

from backend.app.modules.attendance.models import AttendanceRecord, AttendanceStatus
from backend.app.modules.attendance.repository import attendance_repository
from backend.app.modules.attendance.schemas import (
    AttendanceRecordResponse,
    MatchState,
    ObservationItem,
    ObservationSubmission,
)
from backend.app.modules.classrooms.repository import classroom_repository
from backend.app.modules.sessions.models import CaptureSession, SessionStatus
from backend.app.modules.sessions.repository import session_repository
from backend.app.modules.sessions.service import session_service
from backend.app.modules.students.repository import student_repository
from backend.app.modules.users.models import User, UserRole

logger = logging.getLogger(__name__)

# Minimum confidence required for automatic PRESENT_CANDIDATE proposal; below this requires review
CONFIDENCE_THRESHOLD = 0.70


def check_ai_engine_status() -> Dict[str, Any]:
    """
    Check the availability and implementation state of the ai_engine package.
    Documents unresolved external dependencies as mandated by project workflow.
    """
    return {
        "engine_package": "ai_engine",
        "available": False,
        "status": "NOT_IMPLEMENTED",
        "detail": (
            "The ai_engine directory currently contains placeholder structures only (.gitkeep). "
            "Backend integration boundary is implemented according to MANAGE.md §5 contracts "
            "and awaits AI engine pipeline implementation."
        ),
        "contract": {
            "session_id": "string",
            "observations": [
                {
                    "track_id": "string",
                    "candidate_student_id": "string or null",
                    "match_state": "MATCHED | UNKNOWN | INSUFFICIENT_QUALITY | NEEDS_REVIEW",
                    "confidence": "float [0.0 - 1.0]",
                    "reason_codes": "list of strings",
                    "evidence_count": "integer >= 0",
                }
            ],
        },
    }


class AIObservationIntegrationService:
    """
    Backend service managing the ingestion, validation, and proposal transformation
    of AI pipeline observation payloads.
    """

    def __init__(self):
        self.attendance_repo = attendance_repository
        self.session_repo = session_repository
        self.student_repo = student_repository
        self.classroom_repo = classroom_repository

    def authenticate_caller(
        self,
        db: Any,
        session_obj: CaptureSession,
        user: Optional[User] = None,
        permit_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate observation submission using EITHER:
        1. An active, valid cryptographic Capture Permit token bound to this session and classroom.
        2. Authenticated User credentials of the assigned Teacher or an Admin.

        Never logs or exposes the permit token.
        """
        # 1. Check Permit Token Authorization
        if permit_token and permit_token.strip():
            clean_token = permit_token.strip()
            val_res = session_service.validate_permit(db, permit_token=clean_token)
            if not val_res.valid:
                logger.warning(
                    "Observation submission rejected: invalid or expired permit for session '%s'",
                    session_obj.session_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid or unauthorized capture permit: {val_res.message}",
                )

            # Ensure permit is bound to the target session
            if val_res.session_id != session_obj.session_id:
                logger.warning(
                    "Permit session mismatch: permit session '%s' != target session '%s'",
                    val_res.session_id,
                    session_obj.session_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Capture permit token does not match the target session",
                )

            # Ensure permit is bound to the target classroom
            if val_res.classroom_id and val_res.classroom_id != session_obj.classroom_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Capture permit classroom does not match session classroom",
                )

            return {"auth_type": "PERMIT", "permit_id": getattr(val_res, "permit_id", None)}

        # 2. Check User JWT Authorization
        if user:
            if user.role == UserRole.ADMIN:
                return {"auth_type": "USER", "user_id": user.id, "role": "admin"}

            if user.role == UserRole.TEACHER:
                if session_obj.teacher_id != user.id:
                    logger.warning(
                        "Teacher %s denied access to session %s owned by teacher %s",
                        user.id,
                        session_obj.session_id,
                        session_obj.teacher_id,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: You do not have permission to manage this capture session",
                    )
                return {"auth_type": "USER", "user_id": user.id, "role": "teacher"}

        # 3. Neither valid permit nor user provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials or valid capture permit required to submit AI observations",
        )

    def validate_references(
        self,
        db: Any,
        session_identifier: str,
        payload: ObservationSubmission,
    ) -> CaptureSession:
        """
        Validate session and classroom references:
        - Resolves session by identifier string or ID.
        - Automatically transitions and rejects expired sessions.
        - Rejects cancelled or completed sessions.
        - Cross-validates payload session_id and classroom_id if provided.
        """
        session_obj = self.session_repo.get_by_session_id(db, session_id=session_identifier)
        if not session_obj and session_identifier.isdigit():
            session_obj = self.session_repo.get_by_id(db, id=int(session_identifier))

        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Capture session '{session_identifier}' not found",
            )

        # Cross-validate session_id in payload body if supplied
        if payload.session_id and payload.session_id.strip():
            if payload.session_id.strip() != session_obj.session_id and payload.session_id.strip() != str(session_obj.id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Session ID in payload ('{payload.session_id}') does not match target session ('{session_obj.session_id}')",
                )

        # Cross-validate classroom_id if supplied in payload
        if payload.classroom_id is not None:
            if payload.classroom_id != session_obj.classroom_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Classroom ID {payload.classroom_id} in payload does not match session classroom {session_obj.classroom_id}",
                )

        # Check and expire session
        session_obj = session_service._check_and_expire(db, session_obj)

        if session_obj.status != SessionStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit AI observations to a {session_obj.status} session",
            )

        return session_obj

    def map_observation_state(self, obs: ObservationItem) -> Optional[str]:
        """
        Map incoming AI observation match state to authoritative attendance state:
        - MATCHED with confidence >= 0.70 -> PRESENT_CANDIDATE
        - MATCHED with confidence < 0.70 -> NEEDS_REVIEW (weak or marginal match)
        - NEEDS_REVIEW or INSUFFICIENT_QUALITY -> NEEDS_REVIEW
        - UNKNOWN -> None (open-set, unassigned)
        """
        state_str = obs.match_state.value if hasattr(obs.match_state, "value") else str(obs.match_state)

        if state_str == MatchState.UNKNOWN.value:
            return None

        if state_str in (MatchState.NEEDS_REVIEW.value, MatchState.INSUFFICIENT_QUALITY.value):
            return AttendanceStatus.NEEDS_REVIEW.value

        if state_str == MatchState.MATCHED.value:
            if obs.confidence >= CONFIDENCE_THRESHOLD:
                return AttendanceStatus.PRESENT_CANDIDATE.value
            return AttendanceStatus.NEEDS_REVIEW.value

        return AttendanceStatus.NEEDS_REVIEW.value

    def ingest_observations(
        self,
        db: Any,
        session_identifier: str,
        payload: ObservationSubmission,
        user: Optional[User] = None,
        permit_token: Optional[str] = None,
    ) -> List[AttendanceRecordResponse]:
        """
        Process and ingest a batch of AI observations into attendance candidate proposals.
        """
        # 1. Validate session & references
        session_obj = self.validate_references(db, session_identifier=session_identifier, payload=payload)

        # 2. Authenticate caller (permit via secure header or user JWT)
        self.authenticate_caller(db, session_obj=session_obj, user=user, permit_token=permit_token)

        # 3. Retrieve existing records for session to handle intra-batch updates and teacher protection
        existing_records = self.attendance_repo.list_by_session(db, session_id=session_obj.id)
        session_record_map: Dict[int, AttendanceRecord] = {r.student_id: r for r in existing_records}

        processed_student_ids = set()
        results: List[AttendanceRecord] = []

        logger.info(
            "Ingesting %d AI observations for session '%s' in classroom %s",
            len(payload.observations),
            session_obj.session_id,
            session_obj.classroom_id,
        )

        for obs in payload.observations:
            # Skip unassigned tracks or UNKNOWN match state
            if not obs.candidate_student_id or obs.match_state == MatchState.UNKNOWN:
                continue

            # Map match state
            proposed_status = self.map_observation_state(obs)
            if not proposed_status:
                continue

            # Look up student reference
            student = self.student_repo.get_by_student_id(db, student_id=obs.candidate_student_id)
            if not student or not student.is_active:
                logger.info(
                    "Observation candidate student '%s' not found or inactive; skipping safely",
                    obs.candidate_student_id,
                )
                continue

            # Check if record already exists for this student in this session
            existing = session_record_map.get(student.id)

            if existing:
                # RULE: Teacher-finalized attendance is NEVER overwritten by AI observations
                if existing.is_finalized:
                    logger.debug(
                        "Student %s attendance already finalized by teacher; preserving finalization",
                        student.student_id,
                    )
                    if student.id not in processed_student_ids:
                        results.append(existing)
                        processed_student_ids.add(student.id)
                    continue

                # Intra-batch & sequential deduplication: upgrade confidence or state if better
                new_conf = max(existing.confidence or 0.0, obs.confidence)
                new_status = existing.status
                # Upgrade NEEDS_REVIEW to PRESENT_CANDIDATE if a subsequent observation has higher confidence match
                if proposed_status == AttendanceStatus.PRESENT_CANDIDATE.value:
                    new_status = AttendanceStatus.PRESENT_CANDIDATE.value

                update_data = {
                    "status": new_status,
                    "confidence": new_conf,
                    "source": "AI_PROPOSAL",
                }
                updated = self.attendance_repo.update(db, record=existing, update_data=update_data)
                session_record_map[student.id] = updated

                if student.id not in processed_student_ids:
                    results.append(updated)
                    processed_student_ids.add(student.id)
                else:
                    # Update in results list as well
                    for idx, r in enumerate(results):
                        if r.student_id == student.id:
                            results[idx] = updated
                            break
            else:
                # Create initial candidate proposal with is_finalized=False
                record_data = {
                    "session_id": session_obj.id,
                    "session_code": session_obj.session_id,
                    "student_id": student.id,
                    "student_institutional_id": student.student_id,
                    "status": proposed_status,
                    "is_finalized": False,
                    "confidence": obs.confidence,
                    "source": "AI_PROPOSAL",
                }
                created = self.attendance_repo.create(db, record_data=record_data)
                session_record_map[student.id] = created
                results.append(created)
                processed_student_ids.add(student.id)

        # Return responses
        return [
            AttendanceRecordResponse(
                id=r.id,
                session_id=r.session_id,
                session_code=r.session_code,
                student_id=r.student_id,
                student_institutional_id=r.student_institutional_id,
                status=r.status,
                is_finalized=r.is_finalized,
                confidence=r.confidence,
                source=r.source,
                finalized_by_id=r.finalized_by_id,
                finalized_at=r.finalized_at,
                previous_status=r.previous_status,
                notes=r.notes,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in results
        ]


ai_observation_service = AIObservationIntegrationService()
