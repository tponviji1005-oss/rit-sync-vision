"""
Integration tests for authentication endpoints (/api/v1/auth/*).
"""

from backend.app.modules.users.models import UserRole
from backend.app.modules.users.schemas import UserCreate
from backend.app.modules.users.service import user_service


def test_login_and_get_me(client, db_session):
    """Test successful user login and protected /me retrieval."""
    # Seed a test user
    username = "auth_test_user"
    email = "auth_test@rit.edu"
    password = "ValidPassword123!"

    user_service.create_user(
        db_session,
        UserCreate(
            email=email,
            username=username,
            full_name="Auth Test User",
            password=password,
            role=UserRole.TEACHER,
        ),
    )

    # 1. Login with username
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    token = token_data["access_token"]

    # 2. Access protected /me endpoint
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == username
    assert me_data["email"] == email
    assert me_data["role"] == "teacher"
    assert "password" not in me_data
    assert "hashed_password" not in me_data


def test_login_with_email(client, db_session):
    """Verify login works interchangeably with email address."""
    email = "email_login@rit.edu"
    username = "email_login_user"
    password = "SecurePassword123!"

    user_service.create_user(
        db_session,
        UserCreate(
            email=email,
            username=username,
            full_name="Email Login User",
            password=password,
            role=UserRole.TEACHER,
        ),
    )

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": email, "password": password},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_invalid_credentials(client):
    """Verify login rejects invalid passwords and non-existent users."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "non_existent_user", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401
    assert "Incorrect username or password" in resp.json()["detail"]


def test_me_unauthorized_without_token(client):
    """Verify protected endpoints return HTTP 401 when no token is provided."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
