"""
RIT Sync Vision - Offline Synchronization Service
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.attendance.models import AttendanceStatus
from backend.app.modules.attendance.repository import attendance_repository
from backend.app.modules.sessions.models import SessionStatus
from backend.app.modules.sessions.repository import session_repository
from backend.app.modules.students.repository import student_repository
from backend.app.modules.synchronization.models import SyncEvent, SyncEventStatus
from backend.app.modules.synchronization.repository import sync_repository
from backend.app.modules.synchronization.schemas import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncOperationItem,
    SyncOperationResult,
)
from backend.app.modules.users.models import User, UserRole


def compute_payload_hash(item: SyncOperationItem) -> str:
    """
    Compute deterministic SHA-256 hash of the canonical sync event payload.
    Used for idempotency key verification and collision detection.
    """
    raw_str = (
        f"{str(item.session_id).strip()}:"
        f"{item.student_id.strip().upper()}:"
        f"{item.event_type.strip().upper()}:"
        f"{item.status.strip().upper()}:"
        f"{(item.notes or '').strip()}"
    )
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class SyncService:
    """Domain service orchestrating offline attendance synchronization."""

    def process_sync_batch(
        self,
        db: Any,
        batch: SyncBatchRequest,
        current_user: User,
    ) -> SyncBatchResponse:
        """
        Process a batch of offline attendance events idempotently.

        Enforces:
        - Server-side authorization (Teacher/Admin).
        - Stable operation identifier (event_id) idempotency.
        - Session ownership checks.
        - Student reference validation.
        - Preservation of teacher-finalized attendance records (surfaces CONFLICT).
        - Replay safety after simulated network failures.
        - Partial batch resilience (invalid events do not fail valid items).
        """
        role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if role_str not in ("admin", "teacher"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only teachers and administrators can synchronize attendance operations",
            )

        results: List[SyncOperationResult] = []
        synced_count = 0
        duplicate_count = 0
        conflict_count = 0
        rejected_count = 0

        for item in batch.events:
            result = self._process_single_event(db, item, current_user)
            results.append(result)
            if result.status == SyncEventStatus.SYNCED:
                synced_count += 1
            elif result.status == SyncEventStatus.DUPLICATE:
                duplicate_count += 1
            elif result.status == SyncEventStatus.CONFLICT:
                conflict_count += 1
            elif result.status == SyncEventStatus.REJECTED:
                rejected_count += 1

        return SyncBatchResponse(
            total_events=len(batch.events),
            synced_count=synced_count,
            duplicate_count=duplicate_count,
            conflict_count=conflict_count,
            rejected_count=rejected_count,
            results=results,
        )

    def _resolve_session(self, db: Any, session_ref: str):
        ref = str(session_ref).strip()
        sess = session_repository.get_by_session_id(db, ref)
        if not sess and ref.isdigit():
            sess = session_repository.get_by_id(db, int(ref))
        return sess

    def _process_single_event(
        self,
        db: Any,
        item: SyncOperationItem,
        current_user: User,
    ) -> SyncOperationResult:
        server_now = datetime.now(timezone.utc)
        payload_hash = compute_payload_hash(item)

        # 1. Check existing sync event for idempotency
        existing_sync = sync_repository.get_by_event_id(db, item.event_id)
        if existing_sync:
            if existing_sync.payload_hash == payload_hash:
                return SyncOperationResult(
                    event_id=item.event_id,
                    session_id=item.session_id,
                    student_id=item.student_id,
                    status=SyncEventStatus.DUPLICATE,
                    message=f"Duplicate event '{item.event_id}' safely acknowledged",
                    attendance_record_id=existing_sync.attendance_record_id,
                    server_timestamp=server_now,
                )
            else:
                return SyncOperationResult(
                    event_id=item.event_id,
                    session_id=item.session_id,
                    student_id=item.student_id,
                    status=SyncEventStatus.CONFLICT,
                    message=f"Idempotency conflict: event_id '{item.event_id}' already used with differing payload data",
                    attendance_record_id=existing_sync.attendance_record_id,
                    server_timestamp=server_now,
                )

        # 2. Validate Session
        session = self._resolve_session(db, item.session_id)
        if not session:
            return SyncOperationResult(
                event_id=item.event_id,
                session_id=item.session_id,
                student_id=item.student_id,
                status=SyncEventStatus.REJECTED,
                message=f"Session '{item.session_id}' not found",
                server_timestamp=server_now,
            )

        if session.status == SessionStatus.CANCELLED.value:
            return SyncOperationResult(
                event_id=item.event_id,
                session_id=item.session_id,
                student_id=item.student_id,
                status=SyncEventStatus.REJECTED,
                message=f"Session '{item.session_id}' is cancelled",
                server_timestamp=server_now,
            )

        # 3. Session Ownership / Teacher Authorization Check
        role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if role_str == "teacher" and session.teacher_id != current_user.id:
            return SyncOperationResult(
                event_id=item.event_id,
                session_id=item.session_id,
                student_id=item.student_id,
                status=SyncEventStatus.REJECTED,
                message=f"Unauthorized: teacher does not own session '{item.session_id}'",
                server_timestamp=server_now,
            )

        # 4. Validate Student
        student = student_repository.get_by_student_id(db, item.student_id)
        if not student:
            return SyncOperationResult(
                event_id=item.event_id,
                session_id=item.session_id,
                student_id=item.student_id,
                status=SyncEventStatus.REJECTED,
                message=f"Student '{item.student_id}' not found",
                server_timestamp=server_now,
            )

        if not student.is_active:
            return SyncOperationResult(
                event_id=item.event_id,
                session_id=item.session_id,
                student_id=item.student_id,
                status=SyncEventStatus.REJECTED,
                message=f"Student '{item.student_id}' is inactive",
                server_timestamp=server_now,
            )

        # 5. Validate Status
        norm_status = item.status.strip().upper()
        if norm_status not in (AttendanceStatus.PRESENT.value, AttendanceStatus.ABSENT.value):
            return SyncOperationResult(
                event_id=item.event_id,
                session_id=item.session_id,
                student_id=item.student_id,
                status=SyncEventStatus.REJECTED,
                message=f"Invalid attendance status '{item.status}'. Must be PRESENT or ABSENT",
                server_timestamp=server_now,
            )

        # 6. Check existing attendance record & teacher-finalized conflict
        try:
            existing_record = attendance_repository.get_by_session_and_student(db, session.id, student.id)
            if existing_record and existing_record.is_finalized:
                if existing_record.status != norm_status:
                    # MANAGE.md §7: "Conflicts must be surfaced for resolution; never silently overwrite a teacher-finalized record."
                    error_msg = (
                        f"Conflict: student '{item.student_id}' already finalized as "
                        f"'{existing_record.status}' in session; record preserved without overwrite"
                    )
                    sync_repository.create(
                        db,
                        {
                            "event_id": item.event_id,
                            "session_id": session.id,
                            "session_code": session.session_id,
                            "student_id": student.id,
                            "student_institutional_id": student.student_id,
                            "event_type": item.event_type,
                            "status": norm_status,
                            "payload_hash": payload_hash,
                            "sync_status": SyncEventStatus.CONFLICT,
                            "attendance_record_id": existing_record.id,
                            "submitted_by_id": current_user.id,
                            "client_timestamp": item.client_timestamp or server_now,
                            "error_message": error_msg,
                        },
                    )
                    return SyncOperationResult(
                        event_id=item.event_id,
                        session_id=item.session_id,
                        student_id=item.student_id,
                        status=SyncEventStatus.CONFLICT,
                        message=error_msg,
                        attendance_record_id=existing_record.id,
                        server_timestamp=server_now,
                    )
                else:
                    # Already finalized with the same status
                    sync_repository.create(
                        db,
                        {
                            "event_id": item.event_id,
                            "session_id": session.id,
                            "session_code": session.session_id,
                            "student_id": student.id,
                            "student_institutional_id": student.student_id,
                            "event_type": item.event_type,
                            "status": norm_status,
                            "payload_hash": payload_hash,
                            "sync_status": SyncEventStatus.DUPLICATE,
                            "attendance_record_id": existing_record.id,
                            "submitted_by_id": current_user.id,
                            "client_timestamp": item.client_timestamp or server_now,
                            "error_message": "Attendance already finalized with matching status",
                        },
                    )
                    return SyncOperationResult(
                        event_id=item.event_id,
                        session_id=item.session_id,
                        student_id=item.student_id,
                        status=SyncEventStatus.DUPLICATE,
                        message=f"Attendance for student '{item.student_id}' is already finalized with status '{norm_status}'",
                        attendance_record_id=existing_record.id,
                        server_timestamp=server_now,
                    )

            # 7. Create or update attendance record as finalized via OFFLINE_SYNC
            record_id = None
            if existing_record:
                updated = attendance_repository.update(
                    db,
                    existing_record,
                    {
                        "status": norm_status,
                        "is_finalized": True,
                        "source": "OFFLINE_SYNC",
                        "finalized_by_id": current_user.id,
                        "finalized_at": server_now,
                        "previous_status": existing_record.status,
                        "notes": item.notes or existing_record.notes,
                    },
                )
                record_id = updated.id
            else:
                created = attendance_repository.create(
                    db,
                    {
                        "session_id": session.id,
                        "session_code": session.session_id,
                        "student_id": student.id,
                        "student_institutional_id": student.student_id,
                        "status": norm_status,
                        "is_finalized": True,
                        "source": "OFFLINE_SYNC",
                        "finalized_by_id": current_user.id,
                        "finalized_at": server_now,
                        "notes": item.notes,
                    },
                )
                record_id = created.id

            # 8. Record the sync event
            sync_repository.create(
                db,
                {
                    "event_id": item.event_id,
                    "session_id": session.id,
                    "session_code": session.session_id,
                    "student_id": student.id,
                    "student_institutional_id": student.student_id,
                    "event_type": item.event_type,
                    "status": norm_status,
                    "payload_hash": payload_hash,
                    "sync_status": SyncEventStatus.SYNCED,
                    "attendance_record_id": record_id,
                    "submitted_by_id": current_user.id,
                    "client_timestamp": item.client_timestamp or server_now,
                },
            )

            return SyncOperationResult(
                event_id=item.event_id,
                session_id=item.session_id,
                student_id=item.student_id,
                status=SyncEventStatus.SYNCED,
                message=f"Successfully synchronized offline attendance event '{item.event_id}'",
                attendance_record_id=record_id,
                server_timestamp=server_now,
            )
        except HTTPException as he:
            if hasattr(db, "rollback") and callable(db.rollback):
                db.rollback()
            if he.status_code == status.HTTP_409_CONFLICT:
                recheck_sync = sync_repository.get_by_event_id(db, item.event_id)
                if recheck_sync:
                    if recheck_sync.payload_hash == payload_hash:
                        return SyncOperationResult(
                            event_id=item.event_id,
                            session_id=item.session_id,
                            student_id=item.student_id,
                            status=SyncEventStatus.DUPLICATE,
                            message=f"Duplicate event '{item.event_id}' safely acknowledged (concurrent resolution)",
                            attendance_record_id=recheck_sync.attendance_record_id,
                            server_timestamp=server_now,
                        )
                    else:
                        return SyncOperationResult(
                            event_id=item.event_id,
                            session_id=item.session_id,
                            student_id=item.student_id,
                            status=SyncEventStatus.CONFLICT,
                            message=f"Idempotency conflict: event_id '{item.event_id}' already used with differing payload data",
                            attendance_record_id=recheck_sync.attendance_record_id,
                            server_timestamp=server_now,
                        )
            return SyncOperationResult(
                event_id=item.event_id,
                session_id=item.session_id,
                student_id=item.student_id,
                status=SyncEventStatus.REJECTED,
                message=str(he.detail),
                server_timestamp=server_now,
            )
        except Exception as exc:
            if hasattr(db, "rollback") and callable(db.rollback):
                db.rollback()
            return SyncOperationResult(
                event_id=item.event_id,
                session_id=item.session_id,
                student_id=item.student_id,
                status=SyncEventStatus.REJECTED,
                message=f"Processing error: {str(exc)}",
                server_timestamp=server_now,
            )


sync_service = SyncService()
