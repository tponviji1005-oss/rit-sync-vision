"""
RIT Sync Vision - Capture Session and Permit Repository
"""

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.sessions.models import CapturePermit, CaptureSession, SessionStatus

ALLOWED_SESSION_UPDATE_COLUMNS = {
    "status",
    "end_time",
    "camera_stream_url",
    "updated_at",
}


def hash_permit_token(token: str) -> str:
    """Compute SHA-256 hash of a permit token for secure storage and lookup."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def _ensure_sqlite_table(conn):
    """Ensure capture_sessions and capture_permits tables and indices exist in SQLite."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS capture_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            classroom_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            camera_stream_url TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    # SEC-SES-03: Partial unique index to prevent multiple concurrent active sessions per classroom
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_classroom_session
        ON capture_sessions(classroom_id)
        WHERE status = 'ACTIVE'
        """
    )
    # SEC-SES-01: Store token_hash instead of raw permit_token
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS capture_permits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            permit_id TEXT UNIQUE NOT NULL,
            session_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            issued_to_id INTEGER NOT NULL,
            classroom_id INTEGER NOT NULL,
            camera_stream_url TEXT,
            issued_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            is_revoked INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_capture_permits_token_hash
        ON capture_permits(token_hash)
        """
    )
    conn.commit()


def _parse_dt(val) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return datetime.now(timezone.utc)
    return val


def _row_to_session(row) -> Optional[CaptureSession]:
    if not row:
        return None
    return CaptureSession(
        id=row[0],
        session_id=row[1],
        classroom_id=row[2],
        subject_id=row[3],
        teacher_id=row[4],
        status=row[5],
        camera_stream_url=row[6],
        start_time=_parse_dt(row[7]),
        end_time=_parse_dt(row[8]),
        expires_at=_parse_dt(row[9]),
        created_at=_parse_dt(row[10]),
        updated_at=_parse_dt(row[11]),
    )


def _row_to_permit(row) -> Optional[CapturePermit]:
    if not row:
        return None
    return CapturePermit(
        id=row[0],
        permit_id=row[1],
        session_id=row[2],
        token_hash=row[3],
        issued_to_id=row[4],
        classroom_id=row[5],
        camera_stream_url=row[6],
        issued_at=_parse_dt(row[7]),
        expires_at=_parse_dt(row[8]),
        is_revoked=bool(row[9]),
    )


class SessionRepository:
    """Data access repository for CaptureSession and CapturePermit entities."""

    def get_by_id(self, db: Any, id: int) -> Optional[CaptureSession]:
        if hasattr(db, "query") and callable(db.query):
            return db.query(CaptureSession).filter(CaptureSession.id == id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, session_id, classroom_id, subject_id, teacher_id, status, camera_stream_url, "
            "start_time, end_time, expires_at, created_at, updated_at FROM capture_sessions WHERE id = ?",
            (id,),
        )
        return _row_to_session(cursor.fetchone())

    def get_by_session_id(self, db: Any, session_id: str) -> Optional[CaptureSession]:
        normalized_id = session_id.strip()
        if hasattr(db, "query") and callable(db.query):
            return db.query(CaptureSession).filter(CaptureSession.session_id == normalized_id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, session_id, classroom_id, subject_id, teacher_id, status, camera_stream_url, "
            "start_time, end_time, expires_at, created_at, updated_at FROM capture_sessions WHERE session_id = ?",
            (normalized_id,),
        )
        return _row_to_session(cursor.fetchone())

    def get_active_session_in_classroom(self, db: Any, classroom_id: int) -> Optional[CaptureSession]:
        if hasattr(db, "query") and callable(db.query):
            return (
                db.query(CaptureSession)
                .filter(
                    CaptureSession.classroom_id == classroom_id,
                    CaptureSession.status == SessionStatus.ACTIVE.value,
                )
                .first()
            )

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, session_id, classroom_id, subject_id, teacher_id, status, camera_stream_url, "
            "start_time, end_time, expires_at, created_at, updated_at FROM capture_sessions "
            "WHERE classroom_id = ? AND status = 'ACTIVE'",
            (classroom_id,),
        )
        return _row_to_session(cursor.fetchone())

    def list_sessions(
        self,
        db: Any,
        teacher_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CaptureSession]:
        if hasattr(db, "query") and callable(db.query):
            q = db.query(CaptureSession)
            if teacher_id is not None:
                q = q.filter(CaptureSession.teacher_id == teacher_id)
            return q.order_by(CaptureSession.id.desc()).offset(skip).limit(limit).all()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        if teacher_id is not None:
            cursor.execute(
                "SELECT id, session_id, classroom_id, subject_id, teacher_id, status, camera_stream_url, "
                "start_time, end_time, expires_at, created_at, updated_at FROM capture_sessions "
                "WHERE teacher_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (teacher_id, limit, skip),
            )
        else:
            cursor.execute(
                "SELECT id, session_id, classroom_id, subject_id, teacher_id, status, camera_stream_url, "
                "start_time, end_time, expires_at, created_at, updated_at FROM capture_sessions "
                "ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, skip),
            )
        rows = cursor.fetchall()
        return [_row_to_session(r) for r in rows if r]

    def create_session(self, db: Any, session_data: Dict[str, Any]) -> CaptureSession:
        now = datetime.now(timezone.utc)
        # SQLAlchemy branch
        if hasattr(db, "add") and callable(db.add):
            session_obj = CaptureSession(
                session_id=session_data["session_id"].strip(),
                classroom_id=session_data["classroom_id"],
                subject_id=session_data["subject_id"],
                teacher_id=session_data["teacher_id"],
                status=session_data.get("status", SessionStatus.ACTIVE.value),
                camera_stream_url=session_data.get("camera_stream_url"),
                start_time=session_data.get("start_time", now),
                expires_at=session_data["expires_at"],
                created_at=now,
                updated_at=now,
            )
            db.add(session_obj)
            try:
                db.commit()
                db.refresh(session_obj)
                return session_obj
            except Exception as e:
                if hasattr(db, "rollback"):
                    db.rollback()
                err_str = str(e).lower()
                if "uq_active_classroom_session" in err_str or "unique constraint" in err_str:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Classroom with id {session_data['classroom_id']} already has an active capture session",
                    ) from e
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Capture session could not be created due to database conflict",
                ) from e

        # SQLite fallback branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO capture_sessions (
                    session_id, classroom_id, subject_id, teacher_id, status, camera_stream_url,
                    start_time, end_time, expires_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_data["session_id"].strip(),
                    session_data["classroom_id"],
                    session_data["subject_id"],
                    session_data["teacher_id"],
                    session_data.get("status", SessionStatus.ACTIVE.value),
                    session_data.get("camera_stream_url"),
                    session_data.get("start_time", now).isoformat(),
                    None,
                    session_data["expires_at"].isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            db.commit()
            last_id = cursor.lastrowid
            return CaptureSession(
                id=last_id,
                session_id=session_data["session_id"].strip(),
                classroom_id=session_data["classroom_id"],
                subject_id=session_data["subject_id"],
                teacher_id=session_data["teacher_id"],
                status=session_data.get("status", SessionStatus.ACTIVE.value),
                camera_stream_url=session_data.get("camera_stream_url"),
                start_time=session_data.get("start_time", now),
                expires_at=session_data["expires_at"],
                created_at=now,
                updated_at=now,
            )
        except sqlite3.IntegrityError as e:
            if hasattr(db, "rollback"):
                db.rollback()
            err_str = str(e).lower()
            if "uq_active_classroom_session" in err_str or "unique constraint" in err_str:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Classroom with id {session_data['classroom_id']} already has an active capture session",
                ) from e
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Capture session could not be created due to database conflict",
            ) from e

    def update_status(
        self,
        db: Any,
        session: CaptureSession,
        new_status: str,
        end_time: Optional[datetime] = None,
    ) -> CaptureSession:
        now = datetime.now(timezone.utc)
        session.status = new_status
        session.updated_at = now
        if end_time:
            session.end_time = end_time

        if hasattr(db, "commit") and hasattr(session, "__table__"):
            try:
                db.commit()
                db.refresh(session)
                return session
            except Exception as e:
                if hasattr(db, "rollback"):
                    db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Failed to update session status",
                ) from e

        # SQLite fallback branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        end_iso = end_time.isoformat() if end_time else None
        cursor.execute(
            "UPDATE capture_sessions SET status = ?, end_time = ?, updated_at = ? WHERE id = ?",
            (new_status, end_iso, now.isoformat(), session.id),
        )
        db.commit()
        return session

    def create_permit(self, db: Any, permit_data: Dict[str, Any]) -> CapturePermit:
        """
        Store permit record with token_hash at rest (SEC-SES-01).
        Raw permit tokens are never persisted.
        """
        now = datetime.now(timezone.utc)
        token_hash = permit_data["token_hash"]

        if hasattr(db, "add") and callable(db.add):
            permit = CapturePermit(
                permit_id=permit_data["permit_id"].strip(),
                session_id=permit_data["session_id"],
                token_hash=token_hash,
                issued_to_id=permit_data["issued_to_id"],
                classroom_id=permit_data["classroom_id"],
                camera_stream_url=permit_data.get("camera_stream_url"),
                issued_at=permit_data.get("issued_at", now),
                expires_at=permit_data["expires_at"],
                is_revoked=False,
            )
            db.add(permit)
            try:
                db.commit()
                db.refresh(permit)
                return permit
            except Exception as e:
                if hasattr(db, "rollback"):
                    db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Could not issue capture permit due to conflict",
                ) from e

        # SQLite fallback
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO capture_permits (
                    permit_id, session_id, token_hash, issued_to_id, classroom_id,
                    camera_stream_url, issued_at, expires_at, is_revoked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    permit_data["permit_id"].strip(),
                    permit_data["session_id"],
                    token_hash,
                    permit_data["issued_to_id"],
                    permit_data["classroom_id"],
                    permit_data.get("camera_stream_url"),
                    permit_data.get("issued_at", now).isoformat(),
                    permit_data["expires_at"].isoformat(),
                ),
            )
            db.commit()
            last_id = cursor.lastrowid
            return CapturePermit(
                id=last_id,
                permit_id=permit_data["permit_id"].strip(),
                session_id=permit_data["session_id"],
                token_hash=token_hash,
                issued_to_id=permit_data["issued_to_id"],
                classroom_id=permit_data["classroom_id"],
                camera_stream_url=permit_data.get("camera_stream_url"),
                issued_at=permit_data.get("issued_at", now),
                expires_at=permit_data["expires_at"],
                is_revoked=False,
            )
        except sqlite3.IntegrityError as e:
            if hasattr(db, "rollback"):
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Could not issue capture permit due to conflict",
            ) from e

    def get_active_permit_for_session(self, db: Any, session_internal_id: int) -> Optional[CapturePermit]:
        if hasattr(db, "query") and callable(db.query):
            return (
                db.query(CapturePermit)
                .filter(
                    CapturePermit.session_id == session_internal_id,
                    CapturePermit.is_revoked.is_(False),
                )
                .order_by(CapturePermit.id.desc())
                .first()
            )

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, permit_id, session_id, token_hash, issued_to_id, classroom_id, "
            "camera_stream_url, issued_at, expires_at, is_revoked FROM capture_permits "
            "WHERE session_id = ? AND is_revoked = 0 ORDER BY id DESC LIMIT 1",
            (session_internal_id,),
        )
        return _row_to_permit(cursor.fetchone())

    def get_permit_by_hash(self, db: Any, token_hash: str) -> Optional[CapturePermit]:
        """Lookup capture permit by SHA-256 token_hash (SEC-SES-01)."""
        if hasattr(db, "query") and callable(db.query):
            return db.query(CapturePermit).filter(CapturePermit.token_hash == token_hash).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, permit_id, session_id, token_hash, issued_to_id, classroom_id, "
            "camera_stream_url, issued_at, expires_at, is_revoked FROM capture_permits "
            "WHERE token_hash = ?",
            (token_hash,),
        )
        return _row_to_permit(cursor.fetchone())

    def revoke_permit_for_session(self, db: Any, session_internal_id: int) -> None:
        if hasattr(db, "query") and callable(db.query):
            db.query(CapturePermit).filter(CapturePermit.session_id == session_internal_id).update(
                {"is_revoked": True}
            )
            db.commit()
            return

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "UPDATE capture_permits SET is_revoked = 1 WHERE session_id = ?",
            (session_internal_id,),
        )
        db.commit()


session_repository = SessionRepository()
