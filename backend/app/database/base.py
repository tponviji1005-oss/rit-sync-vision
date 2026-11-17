"""
RIT Sync Vision - Database Declarative Base
"""

try:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        """Base class for all SQLAlchemy declarative models."""
        pass

except ImportError:
    try:
        from sqlalchemy.orm import declarative_base
        Base = declarative_base()
    except ImportError:
        class Base:
            """Fallback declarative base class when SQLAlchemy is not installed."""
            metadata = None
