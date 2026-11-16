"""
RIT Sync Vision - Classroom Repository
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.classrooms.models import Classroom

ALLOWED_CLASSROOM_UPDATE_COLUMNS = {
    "room_number",
    "name",
    "capacity",
    "camera_stream_url",
    "is_active",
}


def _ensure_sqlite_table(conn):
    """Ensure classrooms table exists in fallback SQLite connections."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            capacity INTEGER DEFAULT 60,
            camera_stream_url TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _row_to_classroom(row) -> Optional[Classroom]:
    """Convert an SQLite row tuple to a Classroom model instance."""
    if not row:
        return None
    created_at = row[6]
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at)
        except Exception:
            created_at = datetime.now(timezone.utc)
    updated_at = row[7]
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at)
        except Exception:
            updated_at = datetime.now(timezone.utc)

    return Classroom(
        id=row[0],
        room_number=row[1],
        name=row[2],
        capacity=row[3],
        camera_stream_url=row[4],
        is_active=bool(row[5]),
        created_at=created_at,
        updated_at=updated_at,
    )


class ClassroomRepository:
    """Data access repository for Classroom entities."""

    def get_by_id(self, db: Any, id: int) -> Optional[Classroom]:
        if hasattr(db, "query") and callable(db.query):
            return db.query(Classroom).filter(Classroom.id == id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, room_number, name, capacity, camera_stream_url, is_active, created_at, updated_at "
            "FROM classrooms WHERE id = ?",
            (id,),
        )
        return _row_to_classroom(cursor.fetchone())

    def get_by_room_number(self, db: Any, room_number: str) -> Optional[Classroom]:
        normalized_room = room_number.strip().upper()
        if hasattr(db, "query") and callable(db.query):
            return db.query(Classroom).filter(Classroom.room_number == normalized_room).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, room_number, name, capacity, camera_stream_url, is_active, created_at, updated_at "
            "FROM classrooms WHERE UPPER(room_number) = ?",
            (normalized_room,),
        )
        return _row_to_classroom(cursor.fetchone())

    def list_classrooms(self, db: Any, skip: int = 0, limit: int = 100) -> List[Classroom]:
        if hasattr(db, "query") and callable(db.query):
            return db.query(Classroom).offset(skip).limit(limit).all()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, room_number, name, capacity, camera_stream_url, is_active, created_at, updated_at "
            "FROM classrooms ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, skip),
        )
        rows = cursor.fetchall()
        return [_row_to_classroom(r) for r in rows if r]

    def create(self, db: Any, classroom_data: Dict[str, Any]) -> Classroom:
        now = datetime.now(timezone.utc)
        normalized_room = classroom_data["room_number"].strip().upper()

        # SQLAlchemy branch
        if hasattr(db, "add") and callable(db.add):
            classroom = Classroom(
                room_number=normalized_room,
                name=classroom_data["name"].strip(),
                capacity=classroom_data.get("capacity", 60),
                camera_stream_url=classroom_data.get("camera_stream_url"),
                is_active=classroom_data.get("is_active", True),
                created_at=now,
                updated_at=now,
            )
            db.add(classroom)
            try:
                db.commit()
                db.refresh(classroom)
                return classroom
            except Exception as e:
                if hasattr(db, "rollback"):
                    db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Classroom with this room number already exists",
                ) from e

        # SQLite fallback branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO classrooms (room_number, name, capacity, camera_stream_url, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_room,
                    classroom_data["name"].strip(),
                    classroom_data.get("capacity", 60),
                    classroom_data.get("camera_stream_url"),
                    1 if classroom_data.get("is_active", True) else 0,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            db.commit()
            classroom_id = cursor.lastrowid
            return Classroom(
                id=classroom_id,
                room_number=normalized_room,
                name=classroom_data["name"].strip(),
                capacity=classroom_data.get("capacity", 60),
                camera_stream_url=classroom_data.get("camera_stream_url"),
                is_active=classroom_data.get("is_active", True),
                created_at=now,
                updated_at=now,
            )
        except sqlite3.IntegrityError as e:
            if hasattr(db, "rollback"):
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Classroom with this room number already exists",
            ) from e

    def update(self, db: Any, classroom: Classroom, update_data: Dict[str, Any]) -> Classroom:
        now = datetime.now(timezone.utc)

        # SQLAlchemy branch
        if hasattr(db, "commit") and hasattr(classroom, "__table__"):
            for k, v in update_data.items():
                if k in ALLOWED_CLASSROOM_UPDATE_COLUMNS and hasattr(classroom, k):
                    setattr(classroom, k, v)
            classroom.updated_at = now
            try:
                db.commit()
                db.refresh(classroom)
                return classroom
            except Exception as e:
                if hasattr(db, "rollback"):
                    db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Classroom with this room number already exists",
                ) from e

        # SQLite fallback branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            for k, v in update_data.items():
                if k not in ALLOWED_CLASSROOM_UPDATE_COLUMNS:
                    continue
                val = v
                if isinstance(v, bool):
                    val = 1 if v else 0
                cursor.execute(
                    f"UPDATE classrooms SET {k} = ?, updated_at = ? WHERE id = ?",
                    (val, now.isoformat(), classroom.id),
                )
                setattr(classroom, k, v)
            classroom.updated_at = now
            db.commit()
            return classroom
        except sqlite3.IntegrityError as e:
            if hasattr(db, "rollback"):
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Classroom with this room number already exists",
            ) from e

    def delete(self, db: Any, classroom: Classroom) -> bool:
        if hasattr(db, "delete") and callable(db.delete):
            db.delete(classroom)
            db.commit()
            return True

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM classrooms WHERE id = ?", (classroom.id,))
        db.commit()
        return True


classroom_repository = ClassroomRepository()
