"""
RIT Sync Vision - Capture Session and Permit Business Logic Service
"""

import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from fastapi import HTTPException, status

from backend.app.core.security import create_access_token, decode_access_token
from backend.app.modules.classrooms.repository import classroom_repository
from backend.app.modules.sessions.models import CapturePermit, CaptureSession, SessionStatus
from backend.app.modules.sessions.repository import hash_permit_token, session_repository
from backend.app.modules.sessions.schemas import (
    PermitResponse,
    PermitValidateResponse,
    SessionCreate,
    SessionResponse,
)
from backend.app.modules.subjects.repository import subject_repository
from backend.app.modules.users.models import User, UserRole
from backend.app.modules.users.repository import user_repository


class SessionService:
    """Service handling capture session lifecycle and cryptographic permit management."""

    def __init__(self, repo=session_repository):
        self.repo = repo

    def _resolve_session(self, db: Any, identifier: str) -> CaptureSession:
        """Find session by unique string session_id or integer ID."""
        session_obj = self.repo.get_by_session_id(db, session_id=identifier)
        if not session_obj and identifier.isdigit():
            session_obj = self.repo.get_by_id(db, id=int(identifier))
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Capture session '{identifier}' not found",
            )
        return session_obj

    def _check_and_expire(self, db: Any, session_obj: CaptureSession) -> CaptureSession:
        """Automatically transition an ACTIVE session to EXPIRED if past its expiration."""
        now = datetime.now(timezone.utc)
        if session_obj.status == SessionStatus.ACTIVE.value and session_obj.expires_at:
            exp = session_obj.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
                session_obj = self.repo.update_status(
                    db,
                    session=session_obj,
                    new_status=SessionStatus.EXPIRED.value,
                    end_time=exp,
                )
                self.repo.revoke_permit_for_session(db, session_internal_id=session_obj.id)
        return session_obj

    def _verify_session_access(self, session_obj: CaptureSession, current_user: User) -> None:
        """Enforce that Teachers can only view/manage their own sessions, while Admins have full access."""
        if current_user.role == UserRole.TEACHER and session_obj.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to manage this capture session",
            )

    def create_session(
        self,
        db: Any,
        session_in: SessionCreate,
        current_user: User,
    ) -> SessionResponse:
        """
        Start an authorized capture session and issue a time-bound cryptographic permit.
        Requires authenticated Teacher or Admin.
        """
        # Determine and validate teacher_id
        if current_user.role == UserRole.TEACHER:
            teacher_id = current_user.id
        else:
            teacher_id = session_in.teacher_id or current_user.id

        teacher_user = user_repository.get_by_id(db, user_id=teacher_id)
        if not teacher_user or not teacher_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned teacher is invalid or inactive",
            )

        # Validate Classroom
        classroom = classroom_repository.get_by_id(db, id=session_in.classroom_id)
        if not classroom or not classroom.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Classroom with id {session_in.classroom_id} not found or inactive",
            )

        # Validate Subject
        subject = subject_repository.get_by_id(db, id=session_in.subject_id)
        if not subject or not subject.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject with id {session_in.subject_id} not found or inactive",
            )

        # Application-level check (backed by DB partial unique index SEC-SES-03)
        active_in_room = self.repo.get_active_session_in_classroom(db, classroom_id=classroom.id)
        if active_in_room:
            active_in_room = self._check_and_expire(db, active_in_room)
            if active_in_room.status == SessionStatus.ACTIVE.value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Classroom {classroom.room_number} already has an active capture session ({active_in_room.session_id})",
                )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=session_in.duration_minutes)
        camera_url = session_in.camera_stream_url or classroom.camera_stream_url
        session_code = f"SES-{uuid.uuid4().hex[:8].upper()}"

        session_data = {
            "session_id": session_code,
            "classroom_id": classroom.id,
            "subject_id": subject.id,
            "teacher_id": teacher_id,
            "status": SessionStatus.ACTIVE.value,
            "camera_stream_url": camera_url,
            "start_time": now,
            "expires_at": expires_at,
        }
        # Repository handles database-level partial unique index conflict with HTTP 409
        session_obj = self.repo.create_session(db, session_data=session_data)

        # Issue signed cryptographic capture permit
        permit_id = f"PERMIT-{uuid.uuid4().hex[:10].upper()}"
        permit_token = create_access_token(
            data={
                "sub": teacher_user.username,
                "permit_id": permit_id,
                "session_id": session_obj.session_id,
                "classroom_id": classroom.id,
                "scope": "camera_capture",
            },
            expires_delta=timedelta(minutes=session_in.duration_minutes),
        )

        # SEC-SES-01: Hash permit token before database insertion
        token_hash = hash_permit_token(permit_token)
        permit_data = {
            "permit_id": permit_id,
            "session_id": session_obj.id,
            "token_hash": token_hash,
            "issued_to_id": teacher_id,
            "classroom_id": classroom.id,
            "camera_stream_url": camera_url,
            "issued_at": now,
            "expires_at": expires_at,
        }
        permit_obj = self.repo.create_permit(db, permit_data=permit_data)

        # Token is delivered once to the authorized caller on creation flow
        permit_resp = PermitResponse(
            permit_id=permit_obj.permit_id,
            permit_token=permit_token,
            classroom_id=permit_obj.classroom_id,
            camera_stream_url=permit_obj.camera_stream_url,
            issued_at=permit_obj.issued_at,
            expires_at=permit_obj.expires_at,
            is_valid=True,
        )

        return SessionResponse(
            id=session_obj.id,
            session_id=session_obj.session_id,
            classroom_id=session_obj.classroom_id,
            subject_id=session_obj.subject_id,
            teacher_id=session_obj.teacher_id,
            status=session_obj.status,
            camera_stream_url=session_obj.camera_stream_url,
            start_time=session_obj.start_time,
            end_time=session_obj.end_time,
            expires_at=session_obj.expires_at,
            created_at=session_obj.created_at,
            updated_at=session_obj.updated_at,
            active_permit=permit_resp,
        )

    def get_session(self, db: Any, identifier: str, current_user: User) -> SessionResponse:
        session_obj = self._resolve_session(db, identifier=identifier)
        self._verify_session_access(session_obj, current_user)
        session_obj = self._check_and_expire(db, session_obj)

        permit_resp = None
        permit_obj = self.repo.get_active_permit_for_session(db, session_internal_id=session_obj.id)
        if permit_obj and not permit_obj.is_revoked and session_obj.status == SessionStatus.ACTIVE.value:
            # SEC-SES-04: Do not expose permit_token in general session queries
            permit_resp = PermitResponse(
                permit_id=permit_obj.permit_id,
                permit_token=None,
                classroom_id=permit_obj.classroom_id,
                camera_stream_url=permit_obj.camera_stream_url,
                issued_at=permit_obj.issued_at,
                expires_at=permit_obj.expires_at,
                is_valid=True,
            )

        return SessionResponse(
            id=session_obj.id,
            session_id=session_obj.session_id,
            classroom_id=session_obj.classroom_id,
            subject_id=session_obj.subject_id,
            teacher_id=session_obj.teacher_id,
            status=session_obj.status,
            camera_stream_url=session_obj.camera_stream_url,
            start_time=session_obj.start_time,
            end_time=session_obj.end_time,
            expires_at=session_obj.expires_at,
            created_at=session_obj.created_at,
            updated_at=session_obj.updated_at,
            active_permit=permit_resp,
        )

    def list_sessions(
        self,
        db: Any,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SessionResponse]:
        teacher_filter = current_user.id if current_user.role == UserRole.TEACHER else None
        sessions = self.repo.list_sessions(db, teacher_id=teacher_filter, skip=skip, limit=limit)

        results = []
        for s in sessions:
            s = self._check_and_expire(db, s)
            results.append(
                SessionResponse(
                    id=s.id,
                    session_id=s.session_id,
                    classroom_id=s.classroom_id,
                    subject_id=s.subject_id,
                    teacher_id=s.teacher_id,
                    status=s.status,
                    camera_stream_url=s.camera_stream_url,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    expires_at=s.expires_at,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    active_permit=None,
                )
            )
        return results

    def complete_session(self, db: Any, identifier: str, current_user: User) -> SessionResponse:
        session_obj = self._resolve_session(db, identifier=identifier)
        self._verify_session_access(session_obj, current_user)
        session_obj = self._check_and_expire(db, session_obj)

        if session_obj.status != SessionStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot complete session in '{session_obj.status}' state",
            )

        now = datetime.now(timezone.utc)
        updated = self.repo.update_status(
            db,
            session=session_obj,
            new_status=SessionStatus.COMPLETED.value,
            end_time=now,
        )
        self.repo.revoke_permit_for_session(db, session_internal_id=session_obj.id)
        return self.get_session(db, identifier=updated.session_id, current_user=current_user)

    def cancel_session(self, db: Any, identifier: str, current_user: User) -> SessionResponse:
        session_obj = self._resolve_session(db, identifier=identifier)
        self._verify_session_access(session_obj, current_user)
        session_obj = self._check_and_expire(db, session_obj)

        if session_obj.status != SessionStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel session in '{session_obj.status}' state",
            )

        now = datetime.now(timezone.utc)
        updated = self.repo.update_status(
            db,
            session=session_obj,
            new_status=SessionStatus.CANCELLED.value,
            end_time=now,
        )
        self.repo.revoke_permit_for_session(db, session_internal_id=session_obj.id)
        return self.get_session(db, identifier=updated.session_id, current_user=current_user)

    def get_permit(self, db: Any, identifier: str, current_user: User) -> PermitResponse:
        """
        Retrieve or rotate an active capture permit (SEC-SES-01).
        Because permit tokens are hashed at rest and unrecoverable, an authorized request
        to retrieve a permit safely rotates/reissues a fresh token for the remaining
        session duration, revoking the previous permit.
        """
        session_obj = self._resolve_session(db, identifier=identifier)
        self._verify_session_access(session_obj, current_user)
        session_obj = self._check_and_expire(db, session_obj)

        if session_obj.status != SessionStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No active permit available for session in '{session_obj.status}' state",
            )

        now = datetime.now(timezone.utc)
        exp = session_obj.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        remaining_seconds = max(60, int((exp - now).total_seconds()))

        # Revoke existing permit before rotating
        self.repo.revoke_permit_for_session(db, session_internal_id=session_obj.id)

        # Issue newly rotated permit
        teacher_user = user_repository.get_by_id(db, user_id=session_obj.teacher_id)
        username = teacher_user.username if teacher_user else f"user_{session_obj.teacher_id}"
        permit_id = f"PERMIT-{uuid.uuid4().hex[:10].upper()}"

        new_permit_token = create_access_token(
            data={
                "sub": username,
                "permit_id": permit_id,
                "session_id": session_obj.session_id,
                "classroom_id": session_obj.classroom_id,
                "scope": "camera_capture",
            },
            expires_delta=timedelta(seconds=remaining_seconds),
        )

        token_hash = hash_permit_token(new_permit_token)
        permit_data = {
            "permit_id": permit_id,
            "session_id": session_obj.id,
            "token_hash": token_hash,
            "issued_to_id": session_obj.teacher_id,
            "classroom_id": session_obj.classroom_id,
            "camera_stream_url": session_obj.camera_stream_url,
            "issued_at": now,
            "expires_at": session_obj.expires_at,
        }
        new_permit = self.repo.create_permit(db, permit_data=permit_data)

        return PermitResponse(
            permit_id=new_permit.permit_id,
            permit_token=new_permit_token,
            classroom_id=new_permit.classroom_id,
            camera_stream_url=new_permit.camera_stream_url,
            issued_at=new_permit.issued_at,
            expires_at=new_permit.expires_at,
            is_valid=True,
        )

    def validate_permit(self, db: Any, permit_token: str) -> PermitValidateResponse:
        """
        Validate whether a capture permit token is authorized for camera processing.
        Ensures AI and ingestion pipelines only receive frames under active permits.
        SEC-SES-01: Validates cryptographic signature, computes SHA-256 hash, and performs
        constant-time comparison against database record.
        """
        # Cryptographic signature & mandatory exp check
        try:
            payload = decode_access_token(permit_token.strip())
            if not payload:
                return PermitValidateResponse(
                    valid=False,
                    message="Invalid, expired, or tampered permit token signature",
                )
        except Exception:
            return PermitValidateResponse(
                valid=False,
                message="Invalid, expired, or tampered permit token signature",
            )

        # SEC-SES-01: Hash incoming token and query by hash
        token_hash = hash_permit_token(permit_token)
        permit_obj = self.repo.get_permit_by_hash(db, token_hash=token_hash)
        if not permit_obj or permit_obj.is_revoked:
            return PermitValidateResponse(
                valid=False,
                message="Capture permit has been revoked or record does not exist",
            )

        # Constant-time comparison
        if not hmac.compare_digest(permit_obj.token_hash, token_hash):
            return PermitValidateResponse(
                valid=False,
                message="Capture permit hash mismatch",
            )

        # Check permit expiration
        now = datetime.now(timezone.utc)
        exp = permit_obj.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            return PermitValidateResponse(
                valid=False,
                message="Capture permit has expired",
            )

        # Verify underlying session
        session_obj = self.repo.get_by_id(db, id=permit_obj.session_id)
        if not session_obj:
            return PermitValidateResponse(
                valid=False,
                message="Associated capture session not found",
            )

        session_obj = self._check_and_expire(db, session_obj)
        if session_obj.status != SessionStatus.ACTIVE.value:
            return PermitValidateResponse(
                valid=False,
                session_id=session_obj.session_id,
                message=f"Capture session is no longer active (status: {session_obj.status})",
            )

        return PermitValidateResponse(
            valid=True,
            session_id=session_obj.session_id,
            classroom_id=permit_obj.classroom_id,
            camera_stream_url=permit_obj.camera_stream_url,
            message="Permit is valid and authorized for camera capture",
        )


session_service = SessionService()
