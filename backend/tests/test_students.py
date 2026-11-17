"""
Integration and regression tests for Student Management module (/api/v1/students/*).
"""

import pytest
from fastapi import HTTPException

from backend.app.core.security import create_access_token
from backend.app.modules.students.models import Student
from backend.app.modules.students.repository import student_repository
from backend.app.modules.students.schemas import StudentCreate
from backend.app.modules.students.service import student_service
from backend.app.modules.users.models import UserRole
from backend.app.modules.users.schemas import UserCreate
from backend.app.modules.users.service import user_service


@pytest.fixture
def auth_tokens(db_session):
    """Seed test admin and teacher users and return their JWT tokens."""
    admin_name = "stu_test_admin"
    teacher_name = "stu_test_teacher"

    # Seed Admin if not exists
    if not user_service.get_by_username(db_session, admin_name):
        user_service.create_user(
            db_session,
            UserCreate(
                email="stu_admin@rit.edu",
                username=admin_name,
                full_name="Student Test Admin",
                password="AdminPassword123!",
                role=UserRole.ADMIN,
            ),
        )

    # Seed Teacher if not exists
    if not user_service.get_by_username(db_session, teacher_name):
        user_service.create_user(
            db_session,
            UserCreate(
                email="stu_teacher@rit.edu",
                username=teacher_name,
                full_name="Student Test Teacher",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    admin_token = create_access_token(data={"sub": admin_name, "role": "admin"})
    teacher_token = create_access_token(data={"sub": teacher_name, "role": "teacher"})
    return {"admin": admin_token, "teacher": teacher_token}


def test_admin_create_student(client, auth_tokens):
    """Verify Admin can register a new student and no biometric data is stored."""
    token = auth_tokens["admin"]
    resp = client.post(
        "/api/v1/students/",
        json={
            "student_id": "RIT2026CS001",
            "first_name": "Aarav",
            "last_name": "Patel",
            "email": "aarav.patel@rit.edu",
            "is_active": True,
            "is_enrolled": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["student_id"] == "RIT2026CS001"
    assert data["first_name"] == "Aarav"
    assert data["last_name"] == "Patel"
    assert data["email"] == "aarav.patel@rit.edu"
    assert data["is_active"] is True
    assert data["is_enrolled"] is False

    # Strictly verify no biometric fields exist in the response
    assert "face_template" not in data
    assert "embedding" not in data
    assert "image" not in data


def test_teacher_cannot_create_student(client, auth_tokens):
    """Verify Teacher cannot create students (HTTP 403 Forbidden)."""
    token = auth_tokens["teacher"]
    resp = client.post(
        "/api/v1/students/",
        json={
            "student_id": "RIT2026CS002",
            "first_name": "Priya",
            "last_name": "Nair",
            "email": "priya.nair@rit.edu",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_duplicate_student_id_rejected(client, auth_tokens):
    """Verify duplicate student_id returns HTTP 400 Bad Request."""
    token = auth_tokens["admin"]

    # Initial student creation
    client.post(
        "/api/v1/students/",
        json={
            "student_id": "RIT2026CS003",
            "first_name": "Vikram",
            "last_name": "Singh",
            "email": "vikram.singh@rit.edu",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Attempt to register duplicate student_id
    dup_resp = client.post(
        "/api/v1/students/",
        json={
            "student_id": "RIT2026CS003",
            "first_name": "Vikram",
            "last_name": "Different",
            "email": "different.email@rit.edu",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dup_resp.status_code == 400
    assert "already registered" in dup_resp.json()["detail"]


def test_duplicate_student_email_rejected(client, auth_tokens):
    """Verify duplicate email returns HTTP 400 Bad Request."""
    token = auth_tokens["admin"]

    # Initial student creation
    client.post(
        "/api/v1/students/",
        json={
            "student_id": "RIT2026CS004",
            "first_name": "Rohan",
            "last_name": "Gupta",
            "email": "rohan.gupta@rit.edu",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Duplicate email with different student_id
    dup_resp = client.post(
        "/api/v1/students/",
        json={
            "student_id": "RIT2026CS005",
            "first_name": "Another",
            "last_name": "Gupta",
            "email": "rohan.gupta@rit.edu",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dup_resp.status_code == 400
    assert "email is already registered" in dup_resp.json()["detail"]


def test_list_students_as_teacher_and_admin(client, auth_tokens):
    """Verify both Teacher and Admin can list students."""
    # List as Teacher
    t_resp = client.get(
        "/api/v1/students/",
        headers={"Authorization": f"Bearer {auth_tokens['teacher']}"},
    )
    assert t_resp.status_code == 200
    assert isinstance(t_resp.json(), list)

    # List as Admin
    a_resp = client.get(
        "/api/v1/students/",
        headers={"Authorization": f"Bearer {auth_tokens['admin']}"},
    )
    assert a_resp.status_code == 200
    assert isinstance(a_resp.json(), list)


def test_get_student_by_string_student_id(client, auth_tokens):
    """
    Regression test for ISSUE-01:
    Verify GET /api/v1/students/{student_id} retrieves details using institutional string student_id.
    """
    token = auth_tokens["admin"]
    student_code = "RIT2026CS006"
    client.post(
        "/api/v1/students/",
        json={
            "student_id": student_code,
            "first_name": "Ananya",
            "last_name": "Deshmukh",
            "email": "ananya.d@rit.edu",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Fetch using string institutional student_id as Teacher
    get_resp = client.get(
        f"/api/v1/students/{student_code}",
        headers={"Authorization": f"Bearer {auth_tokens['teacher']}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["student_id"] == student_code
    assert get_resp.json()["first_name"] == "Ananya"

    # Fetch non-existent string ID -> 404 Not Found
    missing_resp = client.get(
        "/api/v1/students/NON_EXISTENT_RIT_ID",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing_resp.status_code == 404
    assert "not found" in missing_resp.json()["detail"]


def test_admin_update_student_by_string_student_id(client, auth_tokens):
    """
    Regression test for ISSUE-01:
    Verify PUT /api/v1/students/{student_id} updates record using institutional string student_id.
    """
    admin_tok = auth_tokens["admin"]
    teach_tok = auth_tokens["teacher"]
    student_code = "RIT2026CS007"

    client.post(
        "/api/v1/students/",
        json={
            "student_id": student_code,
            "first_name": "Aditya",
            "last_name": "Verma",
            "email": "aditya.v@rit.edu",
        },
        headers={"Authorization": f"Bearer {admin_tok}"},
    )

    # Teacher update attempt -> 403
    t_resp = client.put(
        f"/api/v1/students/{student_code}",
        json={"first_name": "AdityaUpdated"},
        headers={"Authorization": f"Bearer {teach_tok}"},
    )
    assert t_resp.status_code == 403

    # Admin update using string student_id -> 200
    a_resp = client.put(
        f"/api/v1/students/{student_code}",
        json={"first_name": "AdityaUpdated", "is_enrolled": True},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert a_resp.status_code == 200
    assert a_resp.json()["student_id"] == student_code
    assert a_resp.json()["first_name"] == "AdityaUpdated"
    assert a_resp.json()["is_enrolled"] is True


def test_admin_delete_student_by_string_student_id(client, auth_tokens):
    """
    Regression test for ISSUE-01:
    Verify DELETE /api/v1/students/{student_id} deletes record using institutional string student_id.
    """
    admin_tok = auth_tokens["admin"]
    teach_tok = auth_tokens["teacher"]
    student_code = "RIT2026CS008"

    client.post(
        "/api/v1/students/",
        json={
            "student_id": student_code,
            "first_name": "Meera",
            "last_name": "Joshi",
            "email": "meera.j@rit.edu",
        },
        headers={"Authorization": f"Bearer {admin_tok}"},
    )

    # Teacher delete attempt -> 403
    t_resp = client.delete(
        f"/api/v1/students/{student_code}",
        headers={"Authorization": f"Bearer {teach_tok}"},
    )
    assert t_resp.status_code == 403

    # Admin delete using string student_id -> 200
    a_resp = client.delete(
        f"/api/v1/students/{student_code}",
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert a_resp.status_code == 200

    # Ensure record is deleted and subsequent GET returns 404
    get_resp = client.get(
        f"/api/v1/students/{student_code}",
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert get_resp.status_code == 404


def test_unauthenticated_student_access_rejected(client):
    """Verify unauthenticated requests are rejected with HTTP 401."""
    resp = client.get("/api/v1/students/")
    assert resp.status_code == 401


def test_student_integrity_error_handling(db_session):
    """
    Verify that if a direct database insert causes a uniqueness conflict,
    the repository rolls back and raises HTTP 409 Conflict.
    """
    data = {
        "student_id": "RIT_CONFLICT_01",
        "first_name": "Conflict",
        "last_name": "Student",
        "email": "conflict.student@rit.edu",
        "is_active": True,
        "is_enrolled": False,
    }

    # First insert succeeds
    student_repository.create(db_session, student_data=data)

    # Second direct insert with duplicate student_id must trigger HTTP 409
    with pytest.raises(HTTPException) as exc_info:
        student_repository.create(db_session, student_data=data)

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail
