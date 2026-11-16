"""
RIT Sync Vision - Student Repository
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.students.models import Student

ALLOWED_STUDENT_UPDATE_COLUMNS = {
    "first_name",
    "last_name",
    "email",
    "is_active",
    "is_enrolled",
}


def _ensure_sqlite_table(conn):
    """Ensure students table exists in fallback SQLite connections."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1,
            is_enrolled INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _row_to_student(row) -> Optional[Student]:
    """Convert an SQLite row tuple to a Student model instance."""
    if not row:
        return None
    created_at = row[7]
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at)
        except Exception:
            created_at = datetime.now(timezone.utc)
    updated_at = row[8]
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at)
        except Exception:
            updated_at = datetime.now(timezone.utc)

    return Student(
        id=row[0],
        student_id=row[1],
        first_name=row[2],
        last_name=row[3],
        email=row[4],
        is_active=bool(row[5]),
        is_enrolled=bool(row[6]),
        created_at=created_at,
        updated_at=updated_at,
    )


class StudentRepository:
    """Data access repository for Student entities."""

    def get_by_id(self, db: Any, id: int) -> Optional[Student]:
        if hasattr(db, "query") and callable(db.query):
            return db.query(Student).filter(Student.id == id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, student_id, first_name, last_name, email, is_active, is_enrolled, created_at, updated_at "
            "FROM students WHERE id = ?",
            (id,),
        )
        return _row_to_student(cursor.fetchone())

    def get_by_student_id(self, db: Any, student_id: str) -> Optional[Student]:
        normalized_id = student_id.strip()
        if hasattr(db, "query") and callable(db.query):
            return db.query(Student).filter(Student.student_id == normalized_id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, student_id, first_name, last_name, email, is_active, is_enrolled, created_at, updated_at "
            "FROM students WHERE student_id = ?",
            (normalized_id,),
        )
        return _row_to_student(cursor.fetchone())

    def get_by_email(self, db: Any, email: str) -> Optional[Student]:
        if not email:
            return None
        normalized_email = email.strip().lower()
        if hasattr(db, "query") and callable(db.query):
            return db.query(Student).filter(Student.email == normalized_email).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, student_id, first_name, last_name, email, is_active, is_enrolled, created_at, updated_at "
            "FROM students WHERE LOWER(email) = ?",
            (normalized_email,),
        )
        return _row_to_student(cursor.fetchone())

    def list_students(self, db: Any, skip: int = 0, limit: int = 100) -> List[Student]:
        if hasattr(db, "query") and callable(db.query):
            return db.query(Student).offset(skip).limit(limit).all()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, student_id, first_name, last_name, email, is_active, is_enrolled, created_at, updated_at "
            "FROM students ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, skip),
        )
        rows = cursor.fetchall()
        return [_row_to_student(r) for r in rows if r]

    def create(self, db: Any, student_data: Dict[str, Any]) -> Student:
        now = datetime.now(timezone.utc)
        normalized_email = student_data.get("email")
        if normalized_email:
            normalized_email = normalized_email.strip().lower()

        # SQLAlchemy branch
        if hasattr(db, "add") and callable(db.add):
            student = Student(
                student_id=student_data["student_id"].strip(),
                first_name=student_data["first_name"].strip(),
                last_name=student_data["last_name"].strip(),
                email=normalized_email,
                is_active=student_data.get("is_active", True),
                is_enrolled=student_data.get("is_enrolled", False),
                created_at=now,
                updated_at=now,
            )
            db.add(student)
            try:
                db.commit()
                db.refresh(student)
                return student
            except Exception as e:
                if hasattr(db, "rollback"):
                    db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Student with this identifier or email already exists",
                ) from e

        # SQLite fallback branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO students (student_id, first_name, last_name, email, is_active, is_enrolled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_data["student_id"].strip(),
                    student_data["first_name"].strip(),
                    student_data["last_name"].strip(),
                    normalized_email,
                    1 if student_data.get("is_active", True) else 0,
                    1 if student_data.get("is_enrolled", False) else 0,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            db.commit()
            student_id = cursor.lastrowid
            return Student(
                id=student_id,
                student_id=student_data["student_id"].strip(),
                first_name=student_data["first_name"].strip(),
                last_name=student_data["last_name"].strip(),
                email=normalized_email,
                is_active=student_data.get("is_active", True),
                is_enrolled=student_data.get("is_enrolled", False),
                created_at=now,
                updated_at=now,
            )
        except sqlite3.IntegrityError as e:
            if hasattr(db, "rollback"):
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Student with this identifier or email already exists",
            ) from e

    def update(self, db: Any, student: Student, update_data: Dict[str, Any]) -> Student:
        now = datetime.now(timezone.utc)

        # SQLAlchemy branch
        if hasattr(db, "commit") and hasattr(student, "__table__"):
            for k, v in update_data.items():
                if k in ALLOWED_STUDENT_UPDATE_COLUMNS and hasattr(student, k):
                    setattr(student, k, v)
            student.updated_at = now
            db.commit()
            db.refresh(student)
            return student

        # SQLite fallback branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        for k, v in update_data.items():
            if k not in ALLOWED_STUDENT_UPDATE_COLUMNS:
                continue
            val = v
            if isinstance(v, bool):
                val = 1 if v else 0
            cursor.execute(
                f"UPDATE students SET {k} = ?, updated_at = ? WHERE id = ?",
                (val, now.isoformat(), student.id),
            )
            setattr(student, k, v)
        student.updated_at = now
        db.commit()
        return student

    def delete(self, db: Any, student: Student) -> bool:
        if hasattr(db, "delete") and callable(db.delete):
            db.delete(student)
            db.commit()
            return True

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM students WHERE id = ?", (student.id,))
        db.commit()
        return True


student_repository = StudentRepository()
