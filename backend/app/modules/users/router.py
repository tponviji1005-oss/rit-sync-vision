"""
RIT Sync Vision - User Management API Router
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.database.session import get_db
from backend.app.modules.authentication.dependencies import get_current_user, require_admin
from backend.app.modules.users.models import User, UserRole
from backend.app.modules.users.schemas import UserCreate, UserResponse, UserUpdate
from backend.app.modules.users.service import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List Users",
    description="Retrieve all registered users (Admin only).",
)
def list_users(
    skip: int = 0,
    limit: int = 100,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List application users with pagination."""
    return user_service.list_users(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Create a new user account (Admin only).",
)
def create_user(
    user_in: UserCreate,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create a new user account with specified role and credentials."""
    return user_service.create_user(db, user_in=user_in)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get User By ID",
    description="Retrieve user by identifier (Admin or self only).",
)
def get_user_by_id(
    user_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve user details for self or any user if admin."""
    user_role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    if user_role != UserRole.ADMIN.value and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Cannot view other users' profile",
        )
    return user_service.get_by_id(db, user_id=user_id)
