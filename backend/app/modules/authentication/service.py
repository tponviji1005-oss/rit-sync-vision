"""
RIT Sync Vision - Authentication Business Logic Service
"""

from typing import Any, Optional
from backend.app.core.security import create_access_token, verify_password
from backend.app.modules.authentication.schemas import Token
from backend.app.modules.users.models import User
from backend.app.modules.users.repository import user_repository


class AuthService:
    """Service handling user authentication and token creation."""

    def __init__(self, repo=user_repository):
        self.repo = repo

    def authenticate(
        self,
        db: Any,
        username_or_email: str,
        password: str,
    ) -> Optional[User]:
        """
        Authenticate a user by username/email and password.
        Returns the User instance if valid, None otherwise.
        """
        user = self.repo.get_by_username_or_email(db, identifier=username_or_email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def create_token_for_user(self, user: User) -> Token:
        """Issue a new JWT access token containing subject and role claims."""
        token_data = {
            "sub": user.username,
            "role": user.role,
        }
        access_token = create_access_token(data=token_data)
        return Token(access_token=access_token, token_type="bearer")


auth_service = AuthService()
