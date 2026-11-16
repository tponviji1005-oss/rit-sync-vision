"""
Unit tests for security utilities (password hashing and JWT tokens).
"""

import base64
import hashlib
import hmac
import json
from datetime import timedelta
import pytest

from backend.app.core.config import settings
from backend.app.core.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing_and_verification():
    """Verify password hashing is secure, non-reversible, and verifies correctly."""
    plain = "SuperSecretPassword123!"
    hashed = get_password_hash(plain)

    # Password hash must not be equal to plain text
    assert hashed != plain
    assert len(hashed) > 20

    # Verification must succeed for correct password
    assert verify_password(plain, hashed) is True

    # Verification must fail for incorrect password
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False


def test_sec_01_password_hashing_cross_scheme_compatibility():
    """
    Regression test for SEC-01:
    Verify verify_password supports pbkdf2_sha256 format and handles bcrypt cleanly.
    """
    password = "LegacyPasswordToVerify123!"
    # Generate explicit pbkdf2_sha256 hash
    pbkdf2_hash = get_password_hash(password)
    assert verify_password(password, pbkdf2_hash) is True
    assert verify_password("WrongPassword", pbkdf2_hash) is False

    # Verify invalid/malformed hashes return False safely without unhandled crashes
    assert verify_password("Password", "invalid$hash$format") is False
    assert verify_password("Password", "$2b$12$invalidbchashmockstringthatisntvalid") is False


def test_jwt_token_generation_and_decoding():
    """Verify JWT access tokens encode and decode claims accurately."""
    payload = {"sub": "testteacher", "role": "teacher"}
    token = create_access_token(data=payload, expires_delta=timedelta(minutes=15))

    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    decoded = decode_access_token(token)
    assert decoded["sub"] == "testteacher"
    assert decoded["role"] == "teacher"
    assert "exp" in decoded


def test_sec_02_jwt_requires_exp_claim():
    """
    Regression test for SEC-02:
    Verify decode_access_token explicitly requires the exp claim and rejects tokens without it.
    """
    # Create valid signature for token missing "exp"
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = {"sub": "attacker_user", "role": "admin"}  # No exp claim

    def b64(d):
        return base64.urlsafe_b64encode(d).decode().rstrip("=")

    h_b64 = b64(json.dumps(header).encode())
    p_b64 = b64(json.dumps(payload).encode())
    msg = f"{h_b64}.{p_b64}".encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).digest()
    token_without_exp = f"{h_b64}.{p_b64}.{b64(sig)}"

    with pytest.raises(ValueError, match="exp"):
        decode_access_token(token_without_exp)


def test_jwt_expired_token_rejection():
    """Verify expired tokens are rejected."""
    payload = {"sub": "expireduser", "role": "teacher"}
    # Token expired 10 minutes ago
    token = create_access_token(data=payload, expires_delta=timedelta(minutes=-10))

    with pytest.raises(Exception):
        decode_access_token(token)


def test_jwt_tampered_token_rejection():
    """Verify tampered tokens fail signature verification."""
    payload = {"sub": "legituser", "role": "teacher"}
    token = create_access_token(data=payload, expires_delta=timedelta(minutes=15))

    parts = token.split(".")
    # Tamper with the payload part
    tampered_token = f"{parts[0]}.eyJzdWIiOiAiaGFja2VyIiwgInJvbGUiOiAiYWRtaW4ifQ.{parts[2]}"

    with pytest.raises(Exception):
        decode_access_token(tampered_token)
