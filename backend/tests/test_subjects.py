"""
Integration and regression tests for Subject Management module (/api/v1/subjects/*).
"""

import pytest
from fastapi import HTTPException

from backend.app.core.security import create_access_token
from backend.app.modules.subjects.models import Subject
from backend.app.modules.subjects.repository import subject_repository
from backend.app.modules.subjects.schemas import SubjectCreate
from backend.app.modules.subjects.service import subject_service
from backend.app.modules.users.models import UserRole
from backend.app.modules.users.schemas import UserCreate
from backend.app.modules.users.service import user_service


@pytest.fixture
def auth_tokens(db_session):
    """Seed test admin and teacher users and return their JWT tokens."""
    admin_name = "subj_test_admin"
    teacher_name = "subj_test_teacher"

    # Seed Admin if not exists
    if not user_service.get_by_username(db_session, admin_name):
        user_service.create_user(
            db_session,
            UserCreate(
                email="subj_admin@rit.edu",
                username=admin_name,
                full_name="Subject Test Admin",
                password="AdminPassword123!",
                role=UserRole.ADMIN,
            ),
        )

    # Seed Teacher if not exists
    if not user_service.get_by_username(db_session, teacher_name):
        user_service.create_user(
            db_session,
            UserCreate(
                email="subj_teacher@rit.edu",
                username=teacher_name,
                full_name="Subject Test Teacher",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    admin_token = create_access_token(data={"sub": admin_name, "role": "admin"})
    teacher_token = create_access_token(data={"sub": teacher_name, "role": "teacher"})
    return {"admin": admin_token, "teacher": teacher_token}


def test_admin_create_subject(client, auth_tokens):
    """Verify Admin can register a new academic subject."""
    token = auth_tokens["admin"]
    resp = client.post(
        "/api/v1/subjects/",
        json={
            "subject_code": "CS101",
            "name": "Introduction to Computer Science",
            "department": "Computer Science & Engineering",
            "description": "Foundational course on computing principles and algorithms.",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject_code"] == "CS101"
    assert data["name"] == "Introduction to Computer Science"
    assert data["department"] == "Computer Science & Engineering"
    assert data["description"] == "Foundational course on computing principles and algorithms."
    assert data["is_active"] is True
    assert "id" in data


def test_teacher_cannot_create_subject(client, auth_tokens):
    """Verify Teacher cannot create subjects (HTTP 403 Forbidden)."""
    token = auth_tokens["teacher"]
    resp = client.post(
        "/api/v1/subjects/",
        json={
            "subject_code": "CS102",
            "name": "Data Structures",
            "department": "Computer Science & Engineering",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_duplicate_subject_code_rejected(client, auth_tokens):
    """Verify creating a subject with duplicate code fails with HTTP 400."""
    token = auth_tokens["admin"]
    resp1 = client.post(
        "/api/v1/subjects/",
        json={
            "subject_code": "MAT201",
            "name": "Linear Algebra & Calculus",
            "department": "Mathematics",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 201

    # Attempt duplicate with lowercase code
    resp2 = client.post(
        "/api/v1/subjects/",
        json={
            "subject_code": "mat201",
            "name": "Linear Algebra Duplicate",
            "department": "Mathematics",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["detail"]


def test_list_subjects_as_teacher_and_admin(client, auth_tokens):
    """Verify both Teachers and Admins can list registered subjects."""
    # Teacher listing
    t_resp = client.get(
        "/api/v1/subjects/",
        headers={"Authorization": f"Bearer {auth_tokens['teacher']}"},
    )
    assert t_resp.status_code == 200
    assert isinstance(t_resp.json(), list)

    # Admin listing
    a_resp = client.get(
        "/api/v1/subjects/",
        headers={"Authorization": f"Bearer {auth_tokens['admin']}"},
    )
    assert a_resp.status_code == 200
    assert isinstance(a_resp.json(), list)
    assert len(a_resp.json()) >= 1


def test_get_subject_by_id(client, auth_tokens):
    """Verify retrieving subject details by ID."""
    token = auth_tokens["admin"]
    create_resp = client.post(
        "/api/v1/subjects/",
        json={
            "subject_code": "AI301",
            "name": "Artificial Intelligence & Vision",
            "department": "Computer Science & Engineering",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    subj_id = create_resp.json()["id"]

    # Teacher can read subject details
    t_resp = client.get(
        f"/api/v1/subjects/{subj_id}",
        headers={"Authorization": f"Bearer {auth_tokens['teacher']}"},
    )
    assert t_resp.status_code == 200
    assert t_resp.json()["subject_code"] == "AI301"

    # Nonexistent subject returns 404
    not_found_resp = client.get(
        "/api/v1/subjects/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert not_found_resp.status_code == 404
    assert "not found" in not_found_resp.json()["detail"].lower()


def test_admin_update_subject(client, auth_tokens):
    """Verify Admin can update subject details, while Teacher is forbidden."""
    admin_token = auth_tokens["admin"]
    teacher_token = auth_tokens["teacher"]

    create_resp = client.post(
        "/api/v1/subjects/",
        json={
            "subject_code": "PHY101",
            "name": "Engineering Physics",
            "department": "Physics",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    subj_id = create_resp.json()["id"]

    # Teacher forbidden
    t_resp = client.put(
        f"/api/v1/subjects/{subj_id}",
        json={"name": "Teacher Updated Physics"},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert t_resp.status_code == 403

    # Admin successfully updates
    a_resp = client.put(
        f"/api/v1/subjects/{subj_id}",
        json={
            "name": "Advanced Engineering Physics",
            "description": "Updated syllabus with modern optics and quantum mechanics.",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert a_resp.status_code == 200
    data = a_resp.json()
    assert data["name"] == "Advanced Engineering Physics"
    assert data["description"] == "Updated syllabus with modern optics and quantum mechanics."


def test_admin_delete_subject(client, auth_tokens):
    """Verify Admin can delete a subject, while Teacher is forbidden."""
    admin_token = auth_tokens["admin"]
    teacher_token = auth_tokens["teacher"]

    create_resp = client.post(
        "/api/v1/subjects/",
        json={
            "subject_code": "CHM101",
            "name": "Chemistry for Engineers",
            "department": "Chemistry",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    subj_id = create_resp.json()["id"]

    # Teacher forbidden
    t_resp = client.delete(
        f"/api/v1/subjects/{subj_id}",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert t_resp.status_code == 403

    # Admin deletes
    a_resp = client.delete(
        f"/api/v1/subjects/{subj_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert a_resp.status_code == 200
    assert a_resp.json()["status"] == "ok"

    # Verify deleted
    get_resp = client.get(
        f"/api/v1/subjects/{subj_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


def test_unauthenticated_subject_access_rejected(client):
    """Verify unauthenticated requests to subject endpoints are rejected."""
    resp1 = client.get("/api/v1/subjects/")
    assert resp1.status_code == 401

    resp2 = client.post("/api/v1/subjects/", json={"subject_code": "UNAUTH-1", "name": "Unauth"})
    assert resp2.status_code == 401


def test_subject_integrity_error_handling(db_session):
    """Verify repository catches duplicate constraints and rolls back with HTTP 409."""
    # Create first subject
    subject_repository.create(
        db_session,
        {
            "subject_code": "INT-SUB-1",
            "name": "Integrity Test Subject",
            "department": "Testing",
        },
    )

    # Directly invoke create with same code to test IntegrityError handling
    with pytest.raises(HTTPException) as exc_info:
        subject_repository.create(
            db_session,
            {
                "subject_code": "INT-SUB-1",
                "name": "Integrity Test Duplicate",
                "department": "Testing",
            },
        )

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail
