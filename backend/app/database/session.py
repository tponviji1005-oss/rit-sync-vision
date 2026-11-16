"""
RIT Sync Vision - Database Session and Engine Configuration
"""

import os
from pathlib import Path
from typing import Generator
from backend.app.core.config import settings

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session

    connect_args = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        if db_path and db_path != ":memory:" and not db_path.startswith(":"):
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    def get_db() -> Generator[Session, None, None]:
        """
        FastAPI dependency that yields a SQLAlchemy database session.
        Ensures the session is cleanly closed after request completion.
        """
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

except ImportError:
    import sqlite3

    class _MockCursor:
        def __init__(self, cursor):
            self._cursor = cursor

        def fetchone(self):
            return self._cursor.fetchone()

        def fetchall(self):
            return self._cursor.fetchall()

    class _MockSession:
        def __init__(self, connection):
            self.connection = connection

        def close(self):
            if self.connection:
                self.connection.close()

        def commit(self):
            if self.connection:
                self.connection.commit()

        def rollback(self):
            if self.connection:
                self.connection.rollback()

        def execute(self, statement, *args, **kwargs):
            if self.connection:
                # Handle statement string or text()
                sql = str(statement)
                cursor = self.connection.cursor()
                cursor.execute(sql)
                return _MockCursor(cursor)

    engine = None
    SessionLocal = None

    def get_db():
        """
        Fallback SQLite session dependency when SQLAlchemy is not installed.
        """
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        if db_path and db_path != ":memory:" and not db_path.startswith(":"):
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path if db_path else ":memory:", check_same_thread=False)
        session = _MockSession(conn)
        try:
            yield session
        finally:
            session.close()
