"""
Unit tests for backend configuration settings.
"""

import pytest
from backend.app.core.config import Settings, settings


def test_settings_default_values():
    """Verify settings defaults exist and match configuration specifications."""
    assert settings.APP_ENV in ["development", "test"]
    assert isinstance(settings.DEBUG, bool)
    assert settings.BACKEND_HOST == "0.0.0.0"
    assert settings.BACKEND_PORT == 8000
    assert "sqlite" in settings.DATABASE_URL
    assert settings.CONFIDENCE_THRESHOLD == 0.65
    assert settings.STORAGE_DIR == "./storage"
    assert settings.FACE_TEMPLATES_DIR == "./storage/face_templates"
    assert settings.TEMP_DIR == "./storage/temporary"


def test_settings_custom_override():
    """Verify Settings can be instantiated with overridden values."""
    custom = Settings(
        APP_ENV="testing",
        DEBUG=False,
        BACKEND_PORT=9000,
        DATABASE_URL="sqlite:///:memory:",
        CONFIDENCE_THRESHOLD=0.85,
    )
    assert custom.APP_ENV == "testing"
    assert custom.DEBUG is False
    assert custom.BACKEND_PORT == 9000
    assert custom.DATABASE_URL == "sqlite:///:memory:"
    assert custom.CONFIDENCE_THRESHOLD == 0.85


def test_sec_03_production_secret_key_validation():
    """
    Regression test for SEC-03:
    Verify application blocks startup in production if SECRET_KEY is the default placeholder.
    """
    # 1. Production with default secret must raise ValueError
    with pytest.raises(ValueError, match="Insecure SECRET_KEY"):
        Settings(
            APP_ENV="production",
            SECRET_KEY="change-this-secret-key-in-production",
        )

    # 2. Production with strong custom secret must succeed
    prod_custom = Settings(
        APP_ENV="production",
        SECRET_KEY="a-very-strong-production-cryptographic-secret-key-12345",
    )
    assert prod_custom.APP_ENV == "production"
    assert prod_custom.SECRET_KEY == "a-very-strong-production-cryptographic-secret-key-12345"

    # 3. Development/testing with default secret must succeed
    dev_settings = Settings(
        APP_ENV="development",
        SECRET_KEY="change-this-secret-key-in-production",
    )
    assert dev_settings.APP_ENV == "development"
