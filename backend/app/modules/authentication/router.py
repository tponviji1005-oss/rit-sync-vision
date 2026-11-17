"""
RIT Sync Vision - Authentication API Router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.database.session import get_db
from backend.app.modules.authentication.dependencies import get_current_user
from backend.app.modules.authentication.schemas import LoginRequest, Token
from backend.app.modules.authentication.service import auth_service
from backend.app.modules.users.models import User
from backend.app.modules.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=Token,
    summary="User Login",
    description="Authenticate with username/email and password to receive a JWT bearer token.",
)
def login(credentials: LoginRequest, db=Depends(get_db)):
    """Authenticate credentials and issue JWT bearer token."""
    user = auth_service.authenticate(
        db,
        username_or_email=credentials.username,
        password=credentials.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return auth_service.create_token_for_user(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Retrieve details of the currently authenticated user.",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Return profile information for the authenticated subject."""
    return current_user
