"""
RIT Sync Vision - User Business Logic Service
"""

from typing import Any, List, Optional
from fastapi import HTTPException, status

from backend.app.core.security import get_password_hash
from backend.app.modules.users.models import User
from backend.app.modules.users.repository import user_repository
from backend.app.modules.users.schemas import UserCreate, UserUpdate


class UserService:
    """Service handling user management business rules."""

    def __init__(self, repo=user_repository):
        self.repo = repo

    def get_by_id(self, db: Any, user_id: int) -> User:
        user = self.repo.get_by_id(db, user_id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    def get_by_username(self, db: Any, username: str) -> Optional[User]:
        return self.repo.get_by_username(db, username=username)

    def list_users(self, db: Any, skip: int = 0, limit: int = 100) -> List[User]:
        return self.repo.list_users(db, skip=skip, limit=limit)

    def create_user(self, db: Any, user_in: UserCreate) -> User:
        """
        Create a new user with validation and secure password hashing.
        Admin-only operation.
        """
        # Validate unique email
        existing_email = self.repo.get_by_email(db, email=user_in.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered",
            )

        # Validate unique username
        existing_username = self.repo.get_by_username(db, username=user_in.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken",
            )

        # Hash plain text password securely
        hashed_password = get_password_hash(user_in.password)

        user_data = {
            "email": user_in.email,
            "username": user_in.username,
            "full_name": user_in.full_name,
            "hashed_password": hashed_password,
            "role": user_in.role,
            "is_active": user_in.is_active,
        }
        return self.repo.create(db, user_data=user_data)

    def update_user(self, db: Any, user_id: int, user_in: UserUpdate) -> User:
        user = self.get_by_id(db, user_id=user_id)
        update_data = {}

        if user_in.email is not None and user_in.email.lower() != user.email.lower():
            if self.repo.get_by_email(db, user_in.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email is already in use",
                )
            update_data["email"] = user_in.email

        if user_in.full_name is not None:
            update_data["full_name"] = user_in.full_name

        if user_in.role is not None:
            update_data["role"] = user_in.role

        if user_in.is_active is not None:
            update_data["is_active"] = user_in.is_active

        if user_in.password is not None:
            update_data["hashed_password"] = get_password_hash(user_in.password)

        return self.repo.update(db, user=user, update_data=update_data)


user_service = UserService()
