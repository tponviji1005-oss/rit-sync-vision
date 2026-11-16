"""
RIT Sync Vision - Authentication and Authorization Dependencies
"""

from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.params import Depends as DependsParam
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.security import decode_access_token
from backend.app.database.session import get_db
from backend.app.modules.users.models import User, UserRole
from backend.app.modules.users.repository import user_repository

http_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    authorization: Optional[str] = Header(None),
    db=Depends(get_db),
) -> User:
    """
    Extract, decode, and validate the JWT Bearer token.
    Returns the authenticated User model.
    """
    token = None
    if credentials and hasattr(credentials, "credentials") and not isinstance(credentials, DependsParam):
        token = credentials.credentials
    elif authorization and isinstance(authorization, str) and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_repository.get_by_username(db, username=username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def require_role(required_role: UserRole):
    """
    Dependency factory enforcing role-based access control.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
        expected_role = required_role.value if isinstance(required_role, UserRole) else required_role

        if user_role != expected_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {expected_role} role required",
            )
        return current_user

    return role_checker


require_admin = require_role(UserRole.ADMIN)
require_teacher = require_role(UserRole.TEACHER)
