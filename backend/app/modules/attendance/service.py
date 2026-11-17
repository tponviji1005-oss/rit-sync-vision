"""
RIT Sync Vision - Attendance Management Service
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.attendance.models import AttendanceRecord, AttendanceStatus
from backend.app.modules.attendance.repository import attendance_repository
from backend.app.modules.attendance.schemas import (
    AttendanceRecordResponse,
    AttendanceRecordUpdate,
    FinalizeAttendancePayload,
    ManualAttendanceCreate,
    ObservationSubmission,
    SessionAttendanceSummaryResponse,
)
from backend.app.modules.sessions.models import SessionStatus
from backend.app.modules.sessions.repository import session_repository
from backend.app.modules.sessions.service import session_service
from backend.app.modules.students.repository import student_repository
from backend.app.modules.users.models import User, UserRole


class AttendanceService:
    """
    Business logic coordinator for classroom attendance records.
    Enforces project principles:
    1. AI observations propose candidates; only teachers/admins finalize attendance.
    2. NOT_OBSERVED never automatically becomes ABSENT.
    3. Session authorization is strictly enforced for all mutations.
    4. Duplicate records for the same session and student are prevented.
    5. Modifications maintain an audit trail (previous_status, notes, finalized_by_id).
    """

    def __init__(self):
        self.repo = attendance_repository
        self.session_repo = session_repository
        self.student_repo = student_repository

    def _resolve_session(self, db: Any, identifier: str):
        """Resolve capture session by session_id string or integer ID."""
        session_obj = self.session_repo.get_by_session_id(db, session_id=identifier)
        if not session_obj and identifier.isdigit():
            session_obj = self.session_repo.get_by_id(db, id=int(identifier))
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Capture session '{identifier}' not found",
            )
        return session_obj

    def _verify_session_access(self, session_obj: Any, current_user: User) -> None:
        """Enforce that Teachers can only access their own sessions; Admins have full access."""
        if current_user.role == UserRole.TEACHER and session_obj.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to manage attendance for this capture session",
            )

    def _to_response(self, record: AttendanceRecord) -> AttendanceRecordResponse:
        return AttendanceRecordResponse(
            id=record.id,
            session_id=record.session_id,
            session_code=record.session_code,
            student_id=record.student_id,
            student_institutional_id=record.student_institutional_id,
            status=record.status,
            is_finalized=record.is_finalized,
            confidence=record.confidence,
            source=record.source,
            finalized_by_id=record.finalized_by_id,
            finalized_at=record.finalized_at,
            previous_status=record.previous_status,
            notes=record.notes,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def submit_ai_proposals(
        self,
        db: Any,
        session_identifier: str,
        payload: ObservationSubmission,
        current_user: Optional[User] = None,
        permit_token: Optional[str] = None,
    ) -> List[AttendanceRecordResponse]:
        """
        Record AI observation proposals for teacher review.
        Delegates to ai_observation_service for unified validation, security, and ingestion.
        AI proposals NEVER set is_finalized to True and NEVER overwrite teacher-finalized records.
        """
        from backend.app.modules.attendance.ai_integration import ai_observation_service
        return ai_observation_service.ingest_observations(
            db=db,
            session_identifier=session_identifier,
            payload=payload,
            user=current_user,
            permit_token=permit_token,
        )

    def get_session_attendance(
        self,
        db: Any,
        session_identifier: str,
        current_user: User,
    ) -> SessionAttendanceSummaryResponse:
        """
        Retrieve complete attendance state and review summary for a session.
        Enrolled students without observations are listed as NOT_OBSERVED (never inferred as ABSENT).
        """
        session_obj = self._resolve_session(db, identifier=session_identifier)
        self._verify_session_access(session_obj, current_user)
        session_obj = session_service._check_and_expire(db, session_obj)

        # Retrieve all enrolled active students
        all_students = self.student_repo.list_students(db, skip=0, limit=2000)
        active_enrolled = [s for s in all_students if s.is_active]

        # Retrieve existing attendance records
        existing_records = self.repo.list_by_session(db, session_id=session_obj.id)
        records_by_student_id = {r.student_id: r for r in existing_records}

        full_records_response: List[AttendanceRecordResponse] = []
        now = datetime.now(timezone.utc)

        present_candidates = 0
        needs_review = 0
        not_observed = 0
        finalized_present = 0
        finalized_absent = 0

        # Build response including records for active students
        for student in active_enrolled:
            if student.id in records_by_student_id:
                rec = records_by_student_id[student.id]
                resp = self._to_response(rec)
                full_records_response.append(resp)

                if rec.is_finalized:
                    if rec.status == AttendanceStatus.PRESENT.value:
                        finalized_present += 1
                    elif rec.status == AttendanceStatus.ABSENT.value:
                        finalized_absent += 1
                else:
                    if rec.status == AttendanceStatus.PRESENT_CANDIDATE.value:
                        present_candidates += 1
                    elif rec.status == AttendanceStatus.NEEDS_REVIEW.value:
                        needs_review += 1
                    elif rec.status == AttendanceStatus.NOT_OBSERVED.value:
                        not_observed += 1
            else:
                # Student has no observation: represented as NOT_OBSERVED (NOT ABSENT!)
                not_observed += 1
                full_records_response.append(
                    AttendanceRecordResponse(
                        id=0,
                        session_id=session_obj.id,
                        session_code=session_obj.session_id,
                        student_id=student.id,
                        student_institutional_id=student.student_id,
                        status=AttendanceStatus.NOT_OBSERVED.value,
                        is_finalized=False,
                        confidence=None,
                        source="SYSTEM_PENDING",
                        finalized_by_id=None,
                        finalized_at=None,
                        previous_status=None,
                        notes=None,
                        created_at=now,
                        updated_at=now,
                    )
                )

        return SessionAttendanceSummaryResponse(
            session_id=session_obj.id,
            session_code=session_obj.session_id,
            total_enrolled=len(active_enrolled),
            present_candidates=present_candidates,
            needs_review=needs_review,
            not_observed=not_observed,
            finalized_present=finalized_present,
            finalized_absent=finalized_absent,
            records=full_records_response,
        )

    def finalize_attendance(
        self,
        db: Any,
        session_identifier: str,
        payload: FinalizeAttendancePayload,
        current_user: User,
    ) -> List[AttendanceRecordResponse]:
        """
        Batch finalize attendance decisions by an authorized teacher.
        Only PRESENT and ABSENT are valid finalized statuses.
        """
        session_obj = self._resolve_session(db, identifier=session_identifier)
        self._verify_session_access(session_obj, current_user)
        session_obj = session_service._check_and_expire(db, session_obj)

        allowed_final_statuses = {AttendanceStatus.PRESENT.value, AttendanceStatus.ABSENT.value}
        for item in payload.decisions:
            if item.status not in allowed_final_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid finalization status '{item.status}'. Only PRESENT or ABSENT can be finalized.",
                )

        finalized_results: List[AttendanceRecord] = []
        now = datetime.now(timezone.utc)

        for decision in payload.decisions:
            student = self.student_repo.get_by_student_id(db, student_id=decision.student_id)
            if not student:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Student '{decision.student_id}' not found",
                )

            existing = self.repo.get_by_session_and_student(
                db, session_id=session_obj.id, student_id=student.id
            )

            if existing:
                update_data = {
                    "previous_status": existing.status,
                    "status": decision.status,
                    "is_finalized": True,
                    "finalized_by_id": current_user.id,
                    "finalized_at": now,
                    "source": "TEACHER_FINALIZED",
                    "notes": decision.notes or existing.notes,
                }
                updated = self.repo.update(db, record=existing, update_data=update_data)
                finalized_results.append(updated)
            else:
                record_data = {
                    "session_id": session_obj.id,
                    "session_code": session_obj.session_id,
                    "student_id": student.id,
                    "student_institutional_id": student.student_id,
                    "status": decision.status,
                    "is_finalized": True,
                    "confidence": None,
                    "source": "TEACHER_FINALIZED",
                    "finalized_by_id": current_user.id,
                    "finalized_at": now,
                    "previous_status": AttendanceStatus.NOT_OBSERVED.value,
                    "notes": decision.notes,
                }
                created = self.repo.create(db, record_data=record_data)
                finalized_results.append(created)

        return [self._to_response(r) for r in finalized_results]

    def create_manual_record(
        self,
        db: Any,
        session_identifier: str,
        manual_in: ManualAttendanceCreate,
        current_user: User,
    ) -> AttendanceRecordResponse:
        """
        Non-biometric manual attendance entry (e.g. roll call or manual walk-in).
        Immediately creates or updates a teacher-finalized record.
        """
        session_obj = self._resolve_session(db, identifier=session_identifier)
        self._verify_session_access(session_obj, current_user)
        session_obj = session_service._check_and_expire(db, session_obj)

        allowed_statuses = {AttendanceStatus.PRESENT.value, AttendanceStatus.ABSENT.value}
        if manual_in.status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid manual status '{manual_in.status}'. Only PRESENT or ABSENT allowed.",
            )

        student = self.student_repo.get_by_student_id(db, student_id=manual_in.student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student '{manual_in.student_id}' not found",
            )

        now = datetime.now(timezone.utc)
        existing = self.repo.get_by_session_and_student(
            db, session_id=session_obj.id, student_id=student.id
        )

        if existing:
            update_data = {
                "previous_status": existing.status,
                "status": manual_in.status,
                "is_finalized": True,
                "finalized_by_id": current_user.id,
                "finalized_at": now,
                "source": "MANUAL_ENTRY",
                "notes": manual_in.notes or existing.notes,
            }
            updated = self.repo.update(db, record=existing, update_data=update_data)
            return self._to_response(updated)

        record_data = {
            "session_id": session_obj.id,
            "session_code": session_obj.session_id,
            "student_id": student.id,
            "student_institutional_id": student.student_id,
            "status": manual_in.status,
            "is_finalized": True,
            "confidence": None,
            "source": "MANUAL_ENTRY",
            "finalized_by_id": current_user.id,
            "finalized_at": now,
            "previous_status": AttendanceStatus.NOT_OBSERVED.value,
            "notes": manual_in.notes,
        }
        created = self.repo.create(db, record_data=record_data)
        return self._to_response(created)

    def update_record(
        self,
        db: Any,
        record_id: int,
        update_in: AttendanceRecordUpdate,
        current_user: User,
    ) -> AttendanceRecordResponse:
        """
        Modify an existing attendance record with mandatory audit trail notes.
        """
        record = self.repo.get_by_id(db, id=record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attendance record with id {record_id} not found",
            )

        session_obj = self.session_repo.get_by_id(db, id=record.session_id)
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent capture session not found",
            )
        self._verify_session_access(session_obj, current_user)

        allowed_statuses = {AttendanceStatus.PRESENT.value, AttendanceStatus.ABSENT.value}
        if update_in.status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid updated status '{update_in.status}'. Only PRESENT or ABSENT allowed.",
            )

        if not update_in.notes or not update_in.notes.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audit notes are mandatory when modifying an attendance record",
            )

        now = datetime.now(timezone.utc)
        update_data = {
            "previous_status": record.status,
            "status": update_in.status,
            "is_finalized": True,
            "finalized_by_id": current_user.id,
            "finalized_at": now,
            "source": "TEACHER_OVERRIDE",
            "notes": update_in.notes.strip(),
        }
        updated = self.repo.update(db, record=record, update_data=update_data)
        return self._to_response(updated)

    def get_record(self, db: Any, record_id: int, current_user: User) -> AttendanceRecordResponse:
        """Retrieve a specific attendance record by ID."""
        record = self.repo.get_by_id(db, id=record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attendance record with id {record_id} not found",
            )
        session_obj = self.session_repo.get_by_id(db, id=record.session_id)
        if session_obj:
            self._verify_session_access(session_obj, current_user)
        return self._to_response(record)

    def get_student_history(
        self,
        db: Any,
        student_identifier: str,
        current_user: User,
    ) -> List[AttendanceRecordResponse]:
        """
        Retrieve historical attendance records for a student across all sessions.
        Teachers and Admins can query attendance history.
        """
        student = self.student_repo.get_by_student_id(db, student_id=student_identifier)
        if not student and student_identifier.isdigit():
            student = self.student_repo.get_by_id(db, id=int(student_identifier))

        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student '{student_identifier}' not found",
            )

        records = self.repo.list_by_student_institutional_id(db, student_institutional_id=student.student_id)
        return [self._to_response(r) for r in records]


attendance_service = AttendanceService()
