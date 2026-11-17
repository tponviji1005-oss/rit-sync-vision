"""
RIT Sync Vision - Authentication Pydantic Schemas
"""

from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials required for user authentication."""
    username: str = Field(..., description="Username or email address")
    password: str = Field(..., description="Account plain text password")


class Token(BaseModel):
    """JWT bearer token response."""
    access_token: str = Field(..., description="Encoded JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenPayload(BaseModel):
    """Decoded JWT payload data."""
    sub: str = Field(..., description="User identifier (username or id)")
    role: Optional[str] = Field(None, description="Role encoded in the token")
    exp: Optional[int] = Field(None, description="Expiration UNIX timestamp")
