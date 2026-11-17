"""
RIT Sync Vision - Offline Synchronization Repository
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.synchronization.models import SyncEvent, SyncEventStatus

ALLOWED_SYNC_EVENT_UPDATE_COLUMNS = {
    "sync_status",
    "attendance_record_id",
    "error_message",
    "updated_at",
}


def _ensure_sqlite_table(conn):
    """Ensure sync_events table and indexes exist in SQLite fallback mode."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            session_id INTEGER NOT NULL,
            session_code TEXT,
            student_id INTEGER NOT NULL,
            student_institutional_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            sync_status TEXT NOT NULL,
            attendance_record_id INTEGER,
            submitted_by_id INTEGER NOT NULL,
            client_timestamp TEXT NOT NULL,
            server_timestamp TEXT NOT NULL,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_event_id
        ON sync_events(event_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sync_events_session
        ON sync_events(session_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sync_events_student
        ON sync_events(student_id)
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


def _row_to_sync_event(row) -> Optional[SyncEvent]:
    if not row:
        return None
    return SyncEvent(
        id=row[0],
        event_id=row[1],
        session_id=row[2],
        session_code=row[3],
        student_id=row[4],
        student_institutional_id=row[5],
        event_type=row[6],
        status=row[7],
        payload_hash=row[8],
        sync_status=row[9],
        attendance_record_id=row[10],
        submitted_by_id=row[11],
        client_timestamp=_parse_dt(row[12]),
        server_timestamp=_parse_dt(row[13]),
        error_message=row[14],
        created_at=_parse_dt(row[15]),
        updated_at=_parse_dt(row[16]),
    )


class SyncRepository:
    """Data access repository for SyncEvent records."""

    def get_by_event_id(self, db: Any, event_id: str) -> Optional[SyncEvent]:
        """Fetch sync event by its unique client idempotency key."""
        norm_event_id = event_id.strip()
        if hasattr(db, "query") and callable(db.query):
            return db.query(SyncEvent).filter(SyncEvent.event_id == norm_event_id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT id, event_id, session_id, session_code, student_id,
                   student_institutional_id, event_type, status, payload_hash,
                   sync_status, attendance_record_id, submitted_by_id, client_timestamp,
                   server_timestamp, error_message, created_at, updated_at
            FROM sync_events WHERE event_id = ?
            """,
            (norm_event_id,),
        )
        return _row_to_sync_event(cursor.fetchone())

    def get_by_id(self, db: Any, id: int) -> Optional[SyncEvent]:
        """Fetch sync event by primary key id."""
        if hasattr(db, "query") and callable(db.query):
            return db.query(SyncEvent).filter(SyncEvent.id == id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT id, event_id, session_id, session_code, student_id,
                   student_institutional_id, event_type, status, payload_hash,
                   sync_status, attendance_record_id, submitted_by_id, client_timestamp,
                   server_timestamp, error_message, created_at, updated_at
            FROM sync_events WHERE id = ?
            """,
            (id,),
        )
        return _row_to_sync_event(cursor.fetchone())

    def list_by_session(self, db: Any, session_id: int) -> List[SyncEvent]:
        """List all sync events associated with a session."""
        if hasattr(db, "query") and callable(db.query):
            return (
                db.query(SyncEvent)
                .filter(SyncEvent.session_id == session_id)
                .order_by(SyncEvent.id.asc())
                .all()
            )

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT id, event_id, session_id, session_code, student_id,
                   student_institutional_id, event_type, status, payload_hash,
                   sync_status, attendance_record_id, submitted_by_id, client_timestamp,
                   server_timestamp, error_message, created_at, updated_at
            FROM sync_events WHERE session_id = ? ORDER BY id ASC
            """,
            (session_id,),
        )
        return [_row_to_sync_event(r) for r in cursor.fetchall() if r]

    def create(self, db: Any, event_data: Dict[str, Any]) -> SyncEvent:
        """Create a new sync event with unique event_id constraint enforcement."""
        now = datetime.now(timezone.utc)
        event_data = event_data.copy()
        event_data.setdefault("created_at", now)
        event_data.setdefault("updated_at", now)
        event_data.setdefault("server_timestamp", now)
        if not event_data.get("client_timestamp"):
            event_data["client_timestamp"] = now

        # Convert SyncEventStatus enum to string if needed
        if isinstance(event_data.get("sync_status"), SyncEventStatus):
            event_data["sync_status"] = event_data["sync_status"].value

        if hasattr(db, "add") and callable(db.add):
            try:
                from sqlalchemy.exc import IntegrityError
            except ImportError:
                IntegrityError = Exception

            db_obj = SyncEvent(**event_data)
            db.add(db_obj)
            try:
                db.commit()
                db.refresh(db_obj)
                return db_obj
            except IntegrityError:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Sync event '{event_data.get('event_id')}' already exists",
                )

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO sync_events (
                    event_id, session_id, session_code, student_id,
                    student_institutional_id, event_type, status, payload_hash,
                    sync_status, attendance_record_id, submitted_by_id,
                    client_timestamp, server_timestamp, error_message,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_data["event_id"],
                    event_data["session_id"],
                    event_data.get("session_code"),
                    event_data["student_id"],
                    event_data["student_institutional_id"],
                    event_data.get("event_type", "RECORD_ATTENDANCE"),
                    event_data["status"],
                    event_data["payload_hash"],
                    event_data["sync_status"],
                    event_data.get("attendance_record_id"),
                    event_data["submitted_by_id"],
                    event_data["client_timestamp"].isoformat() if hasattr(event_data["client_timestamp"], "isoformat") else str(event_data["client_timestamp"]),
                    event_data["server_timestamp"].isoformat() if hasattr(event_data["server_timestamp"], "isoformat") else str(event_data["server_timestamp"]),
                    event_data.get("error_message"),
                    event_data["created_at"].isoformat() if hasattr(event_data["created_at"], "isoformat") else str(event_data["created_at"]),
                    event_data["updated_at"].isoformat() if hasattr(event_data["updated_at"], "isoformat") else str(event_data["updated_at"]),
                ),
            )
            db.connection.commit()
            record_id = cursor.lastrowid
            return self.get_by_id(db, id=record_id)
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Sync event '{event_data.get('event_id')}' already exists",
            )

    def update(self, db: Any, event: SyncEvent, update_data: Dict[str, Any]) -> SyncEvent:
        """Safely update mutable fields of a sync event."""
        invalid_cols = set(update_data.keys()) - ALLOWED_SYNC_EVENT_UPDATE_COLUMNS
        if invalid_cols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid update fields: {', '.join(sorted(invalid_cols))}",
            )

        update_data = update_data.copy()
        update_data["updated_at"] = datetime.now(timezone.utc)
        if isinstance(update_data.get("sync_status"), SyncEventStatus):
            update_data["sync_status"] = update_data["sync_status"].value

        if hasattr(db, "commit") and callable(db.commit) and hasattr(event, "__table__"):
            for k, v in update_data.items():
                setattr(event, k, v)
            db.commit()
            db.refresh(event)
            return event

        _ensure_sqlite_table(db.connection)
        set_clauses = []
        params = []
        for col, val in update_data.items():
            set_clauses.append(f"{col} = ?")
            if hasattr(val, "isoformat"):
                params.append(val.isoformat())
            else:
                params.append(val)
        params.append(event.id)

        sql = f"UPDATE sync_events SET {', '.join(set_clauses)} WHERE id = ?"
        cursor = db.connection.cursor()
        cursor.execute(sql, tuple(params))
        db.connection.commit()
        return self.get_by_id(db, id=event.id)


sync_repository = SyncRepository()
