"""
RIT Sync Vision - Subject Repository
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.subjects.models import Subject

ALLOWED_SUBJECT_UPDATE_COLUMNS = {
    "subject_code",
    "name",
    "department",
    "description",
    "is_active",
}


def _ensure_sqlite_table(conn):
    """Ensure subjects table exists in fallback SQLite connections."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _row_to_subject(row) -> Optional[Subject]:
    """Convert an SQLite row tuple to a Subject model instance."""
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

    return Subject(
        id=row[0],
        subject_code=row[1],
        name=row[2],
        department=row[3],
        description=row[4],
        is_active=bool(row[5]),
        created_at=created_at,
        updated_at=updated_at,
    )


class SubjectRepository:
    """Data access repository for Subject entities."""

    def get_by_id(self, db: Any, id: int) -> Optional[Subject]:
        if hasattr(db, "query") and callable(db.query):
            return db.query(Subject).filter(Subject.id == id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, subject_code, name, department, description, is_active, created_at, updated_at "
            "FROM subjects WHERE id = ?",
            (id,),
        )
        return _row_to_subject(cursor.fetchone())

    def get_by_subject_code(self, db: Any, subject_code: str) -> Optional[Subject]:
        normalized_code = subject_code.strip().upper()
        if hasattr(db, "query") and callable(db.query):
            return db.query(Subject).filter(Subject.subject_code == normalized_code).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, subject_code, name, department, description, is_active, created_at, updated_at "
            "FROM subjects WHERE UPPER(subject_code) = ?",
            (normalized_code,),
        )
        return _row_to_subject(cursor.fetchone())

    def list_subjects(self, db: Any, skip: int = 0, limit: int = 100) -> List[Subject]:
        if hasattr(db, "query") and callable(db.query):
            return db.query(Subject).offset(skip).limit(limit).all()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, subject_code, name, department, description, is_active, created_at, updated_at "
            "FROM subjects ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, skip),
        )
        rows = cursor.fetchall()
        return [_row_to_subject(r) for r in rows if r]

    def create(self, db: Any, subject_data: Dict[str, Any]) -> Subject:
        now = datetime.now(timezone.utc)
        normalized_code = subject_data["subject_code"].strip().upper()

        # SQLAlchemy branch
        if hasattr(db, "add") and callable(db.add):
            subject = Subject(
                subject_code=normalized_code,
                name=subject_data["name"].strip(),
                department=subject_data.get("department"),
                description=subject_data.get("description"),
                is_active=subject_data.get("is_active", True),
                created_at=now,
                updated_at=now,
            )
            db.add(subject)
            try:
                db.commit()
                db.refresh(subject)
                return subject
            except Exception as e:
                if hasattr(db, "rollback"):
                    db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Subject with this code already exists",
                ) from e

        # SQLite fallback branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO subjects (subject_code, name, department, description, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_code,
                    subject_data["name"].strip(),
                    subject_data.get("department"),
                    subject_data.get("description"),
                    1 if subject_data.get("is_active", True) else 0,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            db.commit()
            subject_id = cursor.lastrowid
            return Subject(
                id=subject_id,
                subject_code=normalized_code,
                name=subject_data["name"].strip(),
                department=subject_data.get("department"),
                description=subject_data.get("description"),
                is_active=subject_data.get("is_active", True),
                created_at=now,
                updated_at=now,
            )
        except sqlite3.IntegrityError as e:
            if hasattr(db, "rollback"):
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Subject with this code already exists",
            ) from e

    def update(self, db: Any, subject: Subject, update_data: Dict[str, Any]) -> Subject:
        now = datetime.now(timezone.utc)

        # SQLAlchemy branch
        if hasattr(db, "commit") and hasattr(subject, "__table__"):
            for k, v in update_data.items():
                if k in ALLOWED_SUBJECT_UPDATE_COLUMNS and hasattr(subject, k):
                    setattr(subject, k, v)
            subject.updated_at = now
            try:
                db.commit()
                db.refresh(subject)
                return subject
            except Exception as e:
                if hasattr(db, "rollback"):
                    db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Subject with this code already exists",
                ) from e

        # SQLite fallback branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            for k, v in update_data.items():
                if k not in ALLOWED_SUBJECT_UPDATE_COLUMNS:
                    continue
                val = v
                if isinstance(v, bool):
                    val = 1 if v else 0
                cursor.execute(
                    f"UPDATE subjects SET {k} = ?, updated_at = ? WHERE id = ?",
                    (val, now.isoformat(), subject.id),
                )
                setattr(subject, k, v)
            subject.updated_at = now
            db.commit()
            return subject
        except sqlite3.IntegrityError as e:
            if hasattr(db, "rollback"):
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Subject with this code already exists",
            ) from e

    def delete(self, db: Any, subject: Subject) -> bool:
        if hasattr(db, "delete") and callable(db.delete):
            db.delete(subject)
            db.commit()
            return True

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM subjects WHERE id = ?", (subject.id,))
        db.commit()
        return True


subject_repository = SubjectRepository()
