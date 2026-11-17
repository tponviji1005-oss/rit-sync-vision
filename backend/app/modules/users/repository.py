"""
RIT Sync Vision - User Repository
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.users.models import User, UserRole

# SEC-05: Whitelist of allowed column names for updates
ALLOWED_UPDATE_COLUMNS = {
    "email",
    "full_name",
    "role",
    "is_active",
    "hashed_password",
}

try:
    from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
except ImportError:
    SQLAlchemyIntegrityError = None


def _ensure_sqlite_table(conn):
    """Ensure users table exists in fallback SQLite connections."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'teacher',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _row_to_user(row) -> Optional[User]:
    """Convert an SQLite row tuple to a User model instance."""
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

    return User(
        id=row[0],
        email=row[1],
        username=row[2],
        full_name=row[3],
        hashed_password=row[4],
        role=row[5],
        is_active=bool(row[6]),
        created_at=created_at,
        updated_at=updated_at,
    )


class UserRepository:
    """Data access repository for User entities."""

    def get_by_id(self, db: Any, user_id: int) -> Optional[User]:
        if hasattr(db, "query") and callable(db.query):
            return db.query(User).filter(User.id == user_id).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, email, username, full_name, hashed_password, role, is_active, created_at, updated_at "
            "FROM users WHERE id = ?",
            (user_id,),
        )
        return _row_to_user(cursor.fetchone())

    def get_by_email(self, db: Any, email: str) -> Optional[User]:
        normalized_email = email.strip().lower()
        if hasattr(db, "query") and callable(db.query):
            return db.query(User).filter(User.email == normalized_email).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, email, username, full_name, hashed_password, role, is_active, created_at, updated_at "
            "FROM users WHERE LOWER(email) = ?",
            (normalized_email,),
        )
        return _row_to_user(cursor.fetchone())

    def get_by_username(self, db: Any, username: str) -> Optional[User]:
        normalized_username = username.strip()
        if hasattr(db, "query") and callable(db.query):
            return db.query(User).filter(User.username == normalized_username).first()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, email, username, full_name, hashed_password, role, is_active, created_at, updated_at "
            "FROM users WHERE username = ?",
            (normalized_username,),
        )
        return _row_to_user(cursor.fetchone())

    def get_by_username_or_email(self, db: Any, identifier: str) -> Optional[User]:
        normalized = identifier.strip()
        normalized_lower = normalized.lower()
        if hasattr(db, "query") and callable(db.query):
            return (
                db.query(User)
                .filter((User.username == normalized) | (User.email == normalized_lower))
                .first()
            )

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, email, username, full_name, hashed_password, role, is_active, created_at, updated_at "
            "FROM users WHERE username = ? OR LOWER(email) = ?",
            (normalized, normalized_lower),
        )
        return _row_to_user(cursor.fetchone())

    def list_users(self, db: Any, skip: int = 0, limit: int = 100) -> List[User]:
        if hasattr(db, "query") and callable(db.query):
            return db.query(User).offset(skip).limit(limit).all()

        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT id, email, username, full_name, hashed_password, role, is_active, created_at, updated_at "
            "FROM users ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, skip),
        )
        rows = cursor.fetchall()
        return [_row_to_user(r) for r in rows if r]

    def create(self, db: Any, user_data: Dict[str, Any]) -> User:
        role_val = user_data.get("role", UserRole.TEACHER)
        if isinstance(role_val, UserRole):
            role_val = role_val.value

        now = datetime.now(timezone.utc)

        # SQLAlchemy ORM creation branch
        if hasattr(db, "add") and callable(db.add):
            user = User(
                email=user_data["email"].strip().lower(),
                username=user_data["username"].strip(),
                full_name=user_data["full_name"].strip(),
                hashed_password=user_data["hashed_password"],
                role=role_val,
                is_active=user_data.get("is_active", True),
                created_at=now,
                updated_at=now,
            )
            db.add(user)
            try:
                db.commit()
                db.refresh(user)
                return user
            except Exception as e:
                # SEC-04: Roll back transaction and return HTTP 409 Conflict
                if hasattr(db, "rollback"):
                    db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email or username already exists",
                ) from e

        # SQLite fallback creation branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (email, username, full_name, hashed_password, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_data["email"].strip().lower(),
                    user_data["username"].strip(),
                    user_data["full_name"].strip(),
                    user_data["hashed_password"],
                    role_val,
                    1 if user_data.get("is_active", True) else 0,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            db.commit()
            user_id = cursor.lastrowid
            return User(
                id=user_id,
                email=user_data["email"].strip().lower(),
                username=user_data["username"].strip(),
                full_name=user_data["full_name"].strip(),
                hashed_password=user_data["hashed_password"],
                role=role_val,
                is_active=user_data.get("is_active", True),
                created_at=now,
                updated_at=now,
            )
        except sqlite3.IntegrityError as e:
            # SEC-04: Roll back and return HTTP 409 Conflict
            if hasattr(db, "rollback"):
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email or username already exists",
            ) from e

    def update(self, db: Any, user: User, update_data: Dict[str, Any]) -> User:
        now = datetime.now(timezone.utc)

        # SQLAlchemy update branch
        if hasattr(db, "commit") and hasattr(user, "__table__"):
            for k, v in update_data.items():
                if k in ALLOWED_UPDATE_COLUMNS and hasattr(user, k):
                    setattr(user, k, v)
            user.updated_at = now
            db.commit()
            db.refresh(user)
            return user

        # SQLite fallback update branch
        _ensure_sqlite_table(db.connection)
        cursor = db.connection.cursor()
        for k, v in update_data.items():
            # SEC-05: Strict column whitelist enforcement
            if k not in ALLOWED_UPDATE_COLUMNS:
                continue
            if k == "role" and isinstance(v, UserRole):
                v = v.value
            cursor.execute(
                f"UPDATE users SET {k} = ?, updated_at = ? WHERE id = ?",
                (v, now.isoformat(), user.id),
            )
            setattr(user, k, v)
        user.updated_at = now
        db.commit()
        return user


user_repository = UserRepository()
