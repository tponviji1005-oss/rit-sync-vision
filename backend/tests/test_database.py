"""
Unit tests for database session and engine initialization.
"""

from backend.app.database.base import Base
from backend.app.database.session import get_db


def test_database_base_exists():
    """Verify that the declarative Base class is properly defined."""
    assert Base is not None


def test_database_session_generator():
    """Verify get_db dependency yields a usable session and cleanly exits."""
    session_gen = get_db()
    session = next(session_gen)
    assert session is not None

    # Verify query execution on isolated database
    result = session.execute("SELECT 1")
    row = result.fetchone()
    assert row is not None
    assert row[0] == 1

    # Verify teardown
    try:
        next(session_gen)
    except StopIteration:
        pass  # Generator completed successfully
