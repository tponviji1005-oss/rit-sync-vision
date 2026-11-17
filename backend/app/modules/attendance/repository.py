"""
RIT Sync Vision - Attendance Repository
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.attendance.models import AttendanceRecord, AttendanceStatus

ALLOWED_ATTENDANCE_UPDATE_COLUMNS = {
    "status",
    "is_finalized",
    "confidence",
    "source",
    "finalized_by_id",
    "finalized_at",
    "previous_status",
    "notes",
    "updated_at",
}


def _ensure_sqlite_table(conn):
    """Ensure attendance_records table and unique index exist in SQLite."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            session_code TEXT,
            student_id INTEGER NOT NULL,
            student_institutional_id TEXT NOT NULL,
            status TEXT NOT NULL,
            is_finalized INTEGER NOT NULL DEFAULT 0,
            confidence REAL,
            source TEXT NOT NULL,
            finalized_by_id INTEGER,
            finalized_at TEXT,
            previous_status TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    # Unique constraint on (session_id, student_id) to prevent duplicate records
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_session_student_attendance
        ON attendance_records(session_id, student_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_attendance_session
        ON attendance_records(session_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_attendance_student_inst
        ON attendance_records(student_institutional_id)
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


def _row_to_attendance(row) -> Optional[AttendanceRecord]:
    if not row:
        return None
    return AttendanceRecord(
        id=row[0],
        session_id=row[1],
        session_code=row[2],
        student_id=row[3],
        student_institutional_id=row[4],
        status=row[5],
        is_finalized=bool(row[6]),
        confidence=row[7],
        source=row[8],
        finalized_by_id=row[9],
        finalized_at=_parse_dt(row[10]),
        previous_status=row[11],
        notes=row[12],
        created_at=_parse_dt(row[13]),
        updated_at=_parse_dt(row[14]),
    )


class AttendanceRepository:
    """Data access repository for AttendanceRecord entities."""

    def get_by_id(self, db: Any, id: int) -> Optional[AttendanceRecord]:
        """Fetch attendance record by primary key ID."""
        if hasattr(db, "query") and callable(db.query):
            return db.query(AttendanceRecord).filter(AttendanceRecord.id == id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, session_id, session_code, student_id, student_institutional_id, "
            "status, is_finalized, confidence, source, finalized_by_id, finalized_at, "
            "previous_status, notes, created_at, updated_at FROM attendance_records WHERE id = ?",
            (id,),
        )
        return _row_to_attendance(cursor.fetchone())

    def get_by_session_and_student(self, db: Any, session_id: int, student_id: int) -> Optional[AttendanceRecord]:
        """Fetch attendance record for a specific session and student."""
        if hasattr(db, "query") and callable(db.query):
            return (
                db.query(AttendanceRecord)
                .filter(
                    AttendanceRecord.session_id == session_id,
                    AttendanceRecord.student_id == student_id,
                )
                .first()
            )

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, session_id, session_code, student_id, student_institutional_id, "
            "status, is_finalized, confidence, source, finalized_by_id, finalized_at, "
            "previous_status, notes, created_at, updated_at FROM attendance_records "
            "WHERE session_id = ? AND student_id = ?",
            (session_id, student_id),
        )
        return _row_to_attendance(cursor.fetchone())

    def list_by_session(self, db: Any, session_id: int) -> List[AttendanceRecord]:
        """List all attendance records associated with a session."""
        if hasattr(db, "query") and callable(db.query):
            return (
                db.query(AttendanceRecord)
                .filter(AttendanceRecord.session_id == session_id)
                .order_by(AttendanceRecord.student_institutional_id.asc())
                .all()
            )

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, session_id, session_code, student_id, student_institutional_id, "
            "status, is_finalized, confidence, source, finalized_by_id, finalized_at, "
            "previous_status, notes, created_at, updated_at FROM attendance_records "
            "WHERE session_id = ? ORDER BY student_institutional_id ASC",
            (session_id,),
        )
        return [_row_to_attendance(r) for r in cursor.fetchall() if r]

    def list_by_student_institutional_id(self, db: Any, student_institutional_id: str) -> List[AttendanceRecord]:
        """List all attendance records for a student across all sessions."""
        norm_id = student_institutional_id.strip()
        if hasattr(db, "query") and callable(db.query):
            return (
                db.query(AttendanceRecord)
                .filter(AttendanceRecord.student_institutional_id == norm_id)
                .order_by(AttendanceRecord.created_at.desc())
                .all()
            )

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, session_id, session_code, student_id, student_institutional_id, "
            "status, is_finalized, confidence, source, finalized_by_id, finalized_at, "
            "previous_status, notes, created_at, updated_at FROM attendance_records "
            "WHERE student_institutional_id = ? ORDER BY id DESC",
            (norm_id,),
        )
        return [_row_to_attendance(r) for r in cursor.fetchall() if r]

    def create(self, db: Any, record_data: Dict[str, Any]) -> AttendanceRecord:
        """Create a new attendance record with duplicate prevention handling."""
        now = datetime.now(timezone.utc)
        record_data = record_data.copy()
        record_data.setdefault("created_at", now)
        record_data.setdefault("updated_at", now)

        if hasattr(db, "add") and callable(db.add):
            try:
                from sqlalchemy.exc import IntegrityError
            except ImportError:
                IntegrityError = Exception

            db_obj = AttendanceRecord(**record_data)
            db.add(db_obj)
            try:
                db.commit()
                db.refresh(db_obj)
                return db_obj
            except IntegrityError:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Attendance record already exists for session {record_data.get('session_id')} and student {record_data.get('student_institutional_id')}",
                )

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO attendance_records (
                    session_id, session_code, student_id, student_institutional_id,
                    status, is_finalized, confidence, source, finalized_by_id,
                    finalized_at, previous_status, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_data["session_id"],
                    record_data.get("session_code"),
                    record_data["student_id"],
                    record_data["student_institutional_id"],
                    record_data["status"],
                    1 if record_data.get("is_finalized") else 0,
                    record_data.get("confidence"),
                    record_data.get("source", "AI_PROPOSAL"),
                    record_data.get("finalized_by_id"),
                    record_data.get("finalized_at").isoformat() if record_data.get("finalized_at") else None,
                    record_data.get("previous_status"),
                    record_data.get("notes"),
                    record_data["created_at"].isoformat() if hasattr(record_data["created_at"], "isoformat") else str(record_data["created_at"]),
                    record_data["updated_at"].isoformat() if hasattr(record_data["updated_at"], "isoformat") else str(record_data["updated_at"]),
                ),
            )
            db.connection.commit()
            record_id = cursor.lastrowid
            return self.get_by_id(db, id=record_id)
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Attendance record already exists for session {record_data.get('session_id')} and student {record_data.get('student_institutional_id')}",
            )

    def update(self, db: Any, record: AttendanceRecord, update_data: Dict[str, Any]) -> AttendanceRecord:
        """Update an existing attendance record safely with whitelisted columns."""
        now = datetime.now(timezone.utc)
        clean_data = {k: v for k, v in update_data.items() if k in ALLOWED_ATTENDANCE_UPDATE_COLUMNS}
        clean_data["updated_at"] = now

        if hasattr(db, "commit") and callable(db.commit) and hasattr(record, "__dict__"):
            for k, v in clean_data.items():
                setattr(record, k, v)
            try:
                db.commit()
                if hasattr(db, "refresh"):
                    db.refresh(record)
                return record
            except Exception as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update attendance record: {str(e)}",
                )

        _ensure_sqlite_table(db.connection)
        set_clauses = []
        params = []
        for col, val in clean_data.items():
            set_clauses.append(f"{col} = ?")
            if isinstance(val, bool):
                params.append(1 if val else 0)
            elif isinstance(val, datetime):
                params.append(val.isoformat())
            else:
                params.append(val)

        params.append(record.id)
        sql = f"UPDATE attendance_records SET {', '.join(set_clauses)} WHERE id = ?"
        cursor = db.connection.cursor()
        cursor.execute(sql, tuple(params))
        db.connection.commit()
        return self.get_by_id(db, id=record.id)


attendance_repository = AttendanceRepository()
