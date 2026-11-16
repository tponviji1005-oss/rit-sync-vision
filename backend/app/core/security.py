"""
RIT Sync Vision - Security Utilities (Password Hashing & JWT)
"""

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from backend.app.core.config import settings

ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


# ---------------------------------------------------------------------------
# Password Hashing & Verification
# ---------------------------------------------------------------------------

def _verify_pbkdf2_hash(plain_password: str, hashed_password: str) -> bool:
    """Verify password against pbkdf2_sha256 format."""
    try:
        parts = hashed_password.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            iterations = int(parts[1])
            salt = parts[2]
            stored_key = parts[3]
            key = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            )
            return secrets.compare_digest(key.hex(), stored_key)
        return False
    except Exception:
        return False


try:
    from passlib.context import CryptContext

    # SEC-01: Support both bcrypt and pbkdf2_sha256 for smooth transitions
    _pwd_context = CryptContext(
        schemes=["bcrypt", "pbkdf2_sha256"],
        deprecated="auto",
    )

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against an existing hash (bcrypt or pbkdf2_sha256)."""
        if not hashed_password or not plain_password:
            return False
        try:
            return _pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return _verify_pbkdf2_hash(plain_password, hashed_password)

    def get_password_hash(password: str) -> str:
        """Hash a password using bcrypt."""
        return _pwd_context.hash(password)

except ImportError:
    # Standard library fallback using PBKDF2-HMAC-SHA256 with random salt
    def get_password_hash(password: str) -> str:
        """
        Hash a password using PBKDF2-HMAC-SHA256 with 100,000 iterations
        and a secure random 16-byte salt.
        """
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return f"pbkdf2_sha256$100000${salt}${key.hex()}"

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a stored PBKDF2 hash using
        constant-time comparison.
        """
        if not hashed_password or not plain_password:
            return False
        return _verify_pbkdf2_hash(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT Token Generation & Verification
# ---------------------------------------------------------------------------

try:
    from jose import JWTError, jwt

    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a signed JWT access token using python-jose."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

    def decode_access_token(token: str) -> Dict[str, Any]:
        """Decode and validate a JWT access token using python-jose."""
        # SEC-02: Enforce presence of exp claim
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if "exp" not in payload:
            raise ValueError("Token missing mandatory expiration (exp) claim")
        return payload

except ImportError:
    # Standard library fallback for HMAC-SHA256 JWT tokens

    def _b64_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    def _b64_decode(data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data.encode("utf-8"))

    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a signed JWT access token using HMAC-SHA256."""
        to_encode = data.copy()
        if expires_delta:
            exp_timestamp = int((datetime.now(timezone.utc) + expires_delta).timestamp())
        else:
            exp_timestamp = int((datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())
        to_encode["exp"] = exp_timestamp

        header = {"alg": ALGORITHM, "typ": "JWT"}
        header_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _b64_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        signature_b64 = _b64_encode(signature)

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def decode_access_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT access token.
        Raises ValueError if the token is invalid, tampered, expired, or missing exp.
        """
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()

        actual_sig = _b64_decode(parts[2])
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Token signature mismatch")

        payload_bytes = _b64_decode(parts[1])
        payload = json.loads(payload_bytes.decode("utf-8"))

        # SEC-02: Require mandatory expiration claim
        if "exp" not in payload:
            raise ValueError("Token missing mandatory expiration (exp) claim")

        now_ts = int(datetime.now(timezone.utc).timestamp())
        if payload["exp"] < now_ts:
            raise ValueError("Token has expired")

        return payload
