"""
Integration tests for user management and RBAC endpoints (/api/v1/users/*).
"""

import pytest
from fastapi import HTTPException
from backend.app.core.security import create_access_token
from backend.app.modules.users.models import UserRole
from backend.app.modules.users.repository import user_repository
from backend.app.modules.users.schemas import UserCreate
from backend.app.modules.users.service import user_service


def test_admin_user_management_flow(client, db_session):
    """Verify Admin can create users and list them, while Teacher cannot."""
    admin_name = "sys_admin"
    admin_email = "admin@rit.edu"
    admin_pass = "AdminSecretPass123!"

    user_service.create_user(
        db_session,
        UserCreate(
            email=admin_email,
            username=admin_name,
            full_name="System Administrator",
            password=admin_pass,
            role=UserRole.ADMIN,
        ),
    )

    admin_token = create_access_token(data={"sub": admin_name, "role": "admin"})

    # 1. Admin creates a new teacher
    create_resp = client.post(
        "/api/v1/users/",
        json={
            "email": "prof_sharma@rit.edu",
            "username": "prof_sharma",
            "full_name": "Prof. Sharma",
            "password": "TeacherPassword123!",
            "role": "teacher",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    created_user = create_resp.json()
    assert created_user["username"] == "prof_sharma"
    assert created_user["role"] == "teacher"
    assert "password" not in created_user
    assert "hashed_password" not in created_user

    # 2. Admin lists users
    list_resp = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    user_list = list_resp.json()
    assert len(user_list) >= 2
    # Ensure no hashes are leaked in listing
    for u in user_list:
        assert "hashed_password" not in u
        assert "password" not in u


def test_rbac_teacher_forbidden(client, db_session):
    """Verify non-admin users cannot create users or list all users."""
    teacher_name = "normal_teacher"
    teacher_email = "teacher@rit.edu"
    teacher_pass = "NormalPass123!"

    user_service.create_user(
        db_session,
        UserCreate(
            email=teacher_email,
            username=teacher_name,
            full_name="Normal Teacher",
            password=teacher_pass,
            role=UserRole.TEACHER,
        ),
    )

    teacher_token = create_access_token(data={"sub": teacher_name, "role": "teacher"})

    # Teacher attempts to list users -> 403 Forbidden
    list_resp = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert list_resp.status_code == 403
    assert "Access denied" in list_resp.json()["detail"]

    # Teacher attempts to create a user -> 403 Forbidden
    create_resp = client.post(
        "/api/v1/users/",
        json={
            "email": "intruder@rit.edu",
            "username": "intruder",
            "full_name": "Intruder User",
            "password": "Password123!",
            "role": "teacher",
        },
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert create_resp.status_code == 403
    assert "Access denied" in create_resp.json()["detail"]


def test_duplicate_user_validation(client, db_session):
    """Verify duplicate email or username is rejected with HTTP 400."""
    admin_name = "dup_test_admin"
    admin_email = "dup_admin@rit.edu"
    admin_pass = "AdminPass123!"

    user_service.create_user(
        db_session,
        UserCreate(
            email=admin_email,
            username=admin_name,
            full_name="Duplicate Test Admin",
            password=admin_pass,
            role=UserRole.ADMIN,
        ),
    )
    admin_token = create_access_token(data={"sub": admin_name, "role": "admin"})

    # Create initial user
    client.post(
        "/api/v1/users/",
        json={
            "email": "unique_email@rit.edu",
            "username": "unique_username",
            "full_name": "Unique User",
            "password": "Password123!",
            "role": "teacher",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Attempt to create with same email
    dup_email_resp = client.post(
        "/api/v1/users/",
        json={
            "email": "unique_email@rit.edu",
            "username": "different_username",
            "full_name": "Different User",
            "password": "Password123!",
            "role": "teacher",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dup_email_resp.status_code == 400
    assert "Email is already registered" in dup_email_resp.json()["detail"]

    # Attempt to create with same username
    dup_name_resp = client.post(
        "/api/v1/users/",
        json={
            "email": "different_email@rit.edu",
            "username": "unique_username",
            "full_name": "Different User",
            "password": "Password123!",
            "role": "teacher",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dup_name_resp.status_code == 400
    assert "Username is already taken" in dup_name_resp.json()["detail"]


def test_sec_04_integrity_error_handling(db_session):
    """
    Regression test for SEC-04:
    Verify that if an insert violates uniqueness constraints at the database level,
    user_repository.create catches the IntegrityError, rolls back, and raises HTTP 409 Conflict.
    """
    user_data = {
        "email": "conflict_user@rit.edu",
        "username": "conflict_user",
        "full_name": "Conflict User",
        "hashed_password": "some_valid_hash_123",
        "role": "teacher",
        "is_active": True,
    }

    # First insert succeeds
    user_repository.create(db_session, user_data=user_data)

    # Second direct insert with duplicate data must raise HTTP 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        user_repository.create(db_session, user_data=user_data)

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail


def test_sec_05_update_column_whitelist(db_session):
    """
    Regression test for SEC-05:
    Verify that update operations only accept whitelisted columns and ignore untrusted keys.
    """
    user = user_repository.create(
        db_session,
        user_data={
            "email": "whitelist_test@rit.edu",
            "username": "whitelist_user",
            "full_name": "Original Name",
            "hashed_password": "hash",
            "role": "teacher",
            "is_active": True,
        },
    )

    # Update with a valid column and an invalid/untrusted column
    updated = user_repository.update(
        db_session,
        user=user,
        update_data={
            "full_name": "Verified Updated Name",
            "injected_column; DROP TABLE users; --": "malicious_value",
            "non_existent_key": "some_value",
        },
    )

    assert updated.full_name == "Verified Updated Name"
    # Ensure invalid keys were never added to the user model
    assert not hasattr(updated, "injected_column; DROP TABLE users; --")
    assert not hasattr(updated, "non_existent_key")
