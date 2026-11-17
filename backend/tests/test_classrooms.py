"""
Integration and regression tests for Classroom Management module (/api/v1/classrooms/*).
"""

import pytest
from fastapi import HTTPException

from backend.app.core.security import create_access_token
from backend.app.modules.classrooms.models import Classroom
from backend.app.modules.classrooms.repository import classroom_repository
from backend.app.modules.classrooms.schemas import ClassroomCreate
from backend.app.modules.classrooms.service import classroom_service
from backend.app.modules.users.models import UserRole
from backend.app.modules.users.schemas import UserCreate
from backend.app.modules.users.service import user_service


@pytest.fixture
def auth_tokens(db_session):
    """Seed test admin and teacher users and return their JWT tokens."""
    admin_name = "room_test_admin"
    teacher_name = "room_test_teacher"

    # Seed Admin if not exists
    if not user_service.get_by_username(db_session, admin_name):
        user_service.create_user(
            db_session,
            UserCreate(
                email="room_admin@rit.edu",
                username=admin_name,
                full_name="Classroom Test Admin",
                password="AdminPassword123!",
                role=UserRole.ADMIN,
            ),
        )

    # Seed Teacher if not exists
    if not user_service.get_by_username(db_session, teacher_name):
        user_service.create_user(
            db_session,
            UserCreate(
                email="room_teacher@rit.edu",
                username=teacher_name,
                full_name="Classroom Test Teacher",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    admin_token = create_access_token(data={"sub": admin_name, "role": "admin"})
    teacher_token = create_access_token(data={"sub": teacher_name, "role": "teacher"})
    return {"admin": admin_token, "teacher": teacher_token}


def test_admin_create_classroom(client, auth_tokens):
    """Verify Admin can register a new classroom and no biometric fields exist."""
    token = auth_tokens["admin"]
    resp = client.post(
        "/api/v1/classrooms/",
        json={
            "room_number": "LH-101",
            "name": "Main Lecture Hall",
            "capacity": 120,
            "camera_stream_url": "rtsp://camera.internal/lh101",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["room_number"] == "LH-101"
    assert data["name"] == "Main Lecture Hall"
    assert data["capacity"] == 120
    assert data["camera_stream_url"] == "rtsp://camera.internal/lh101"
    assert data["is_active"] is True
    assert "id" in data

    # Strictly verify no biometric or raw media fields exist
    assert "face_template" not in data
    assert "embedding" not in data
    assert "image" not in data
    assert "frame" not in data


def test_teacher_cannot_create_classroom(client, auth_tokens):
    """Verify Teacher cannot create classrooms (HTTP 403 Forbidden)."""
    token = auth_tokens["teacher"]
    resp = client.post(
        "/api/v1/classrooms/",
        json={
            "room_number": "LH-102",
            "name": "Second Lecture Hall",
            "capacity": 80,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_duplicate_room_number_rejected(client, auth_tokens):
    """Verify creating a classroom with an existing room_number fails with HTTP 400."""
    token = auth_tokens["admin"]
    resp1 = client.post(
        "/api/v1/classrooms/",
        json={
            "room_number": "CR-201",
            "name": "Classroom 201",
            "capacity": 60,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 201

    # Attempt duplicate
    resp2 = client.post(
        "/api/v1/classrooms/",
        json={
            "room_number": "cr-201",  # case-insensitive check
            "name": "Classroom 201 Duplicate",
            "capacity": 50,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["detail"]


def test_list_classrooms_as_teacher_and_admin(client, auth_tokens):
    """Verify both Teachers and Admins can list classrooms."""
    # List as Teacher
    t_resp = client.get(
        "/api/v1/classrooms/",
        headers={"Authorization": f"Bearer {auth_tokens['teacher']}"},
    )
    assert t_resp.status_code == 200
    assert isinstance(t_resp.json(), list)

    # List as Admin
    a_resp = client.get(
        "/api/v1/classrooms/",
        headers={"Authorization": f"Bearer {auth_tokens['admin']}"},
    )
    assert a_resp.status_code == 200
    assert isinstance(a_resp.json(), list)
    assert len(a_resp.json()) >= 1


def test_get_classroom_by_id(client, auth_tokens):
    """Verify retrieving a classroom by integer ID."""
    token = auth_tokens["admin"]
    create_resp = client.post(
        "/api/v1/classrooms/",
        json={
            "room_number": "LAB-301",
            "name": "AI Systems Laboratory",
            "capacity": 40,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    room_id = create_resp.json()["id"]

    # Teacher can read classroom details
    t_resp = client.get(
        f"/api/v1/classrooms/{room_id}",
        headers={"Authorization": f"Bearer {auth_tokens['teacher']}"},
    )
    assert t_resp.status_code == 200
    assert t_resp.json()["room_number"] == "LAB-301"

    # Nonexistent ID returns 404
    not_found_resp = client.get(
        "/api/v1/classrooms/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert not_found_resp.status_code == 404
    assert "not found" in not_found_resp.json()["detail"].lower()


def test_admin_update_classroom(client, auth_tokens):
    """Verify Admin can update classroom attributes, while Teacher is forbidden."""
    admin_token = auth_tokens["admin"]
    teacher_token = auth_tokens["teacher"]

    create_resp = client.post(
        "/api/v1/classrooms/",
        json={
            "room_number": "CR-401",
            "name": "Old Room Name",
            "capacity": 30,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    room_id = create_resp.json()["id"]

    # Teacher attempt to update -> 403 Forbidden
    t_resp = client.put(
        f"/api/v1/classrooms/{room_id}",
        json={"name": "Teacher Updated Name"},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert t_resp.status_code == 403

    # Admin successfully updates
    a_resp = client.put(
        f"/api/v1/classrooms/{room_id}",
        json={
            "name": "Updated Room Name",
            "capacity": 45,
            "camera_stream_url": "rtsp://camera.internal/cr401",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert a_resp.status_code == 200
    data = a_resp.json()
    assert data["name"] == "Updated Room Name"
    assert data["capacity"] == 45
    assert data["camera_stream_url"] == "rtsp://camera.internal/cr401"


def test_admin_delete_classroom(client, auth_tokens):
    """Verify Admin can delete a classroom, while Teacher is forbidden."""
    admin_token = auth_tokens["admin"]
    teacher_token = auth_tokens["teacher"]

    create_resp = client.post(
        "/api/v1/classrooms/",
        json={
            "room_number": "DEL-501",
            "name": "Room To Delete",
            "capacity": 20,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    room_id = create_resp.json()["id"]

    # Teacher forbidden
    t_resp = client.delete(
        f"/api/v1/classrooms/{room_id}",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert t_resp.status_code == 403

    # Admin deletes
    a_resp = client.delete(
        f"/api/v1/classrooms/{room_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert a_resp.status_code == 200
    assert a_resp.json()["status"] == "ok"

    # Verify deleted
    get_resp = client.get(
        f"/api/v1/classrooms/{room_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


def test_unauthenticated_classroom_access_rejected(client):
    """Verify unauthenticated requests to classroom endpoints are rejected."""
    resp1 = client.get("/api/v1/classrooms/")
    assert resp1.status_code == 401

    resp2 = client.post("/api/v1/classrooms/", json={"room_number": "UNAUTH-1", "name": "Unauth"})
    assert resp2.status_code == 401


def test_classroom_integrity_error_handling(db_session):
    """Verify repository catches duplicate constraints and rolls back with HTTP 409."""
    # Create first room
    classroom_repository.create(
        db_session,
        {
            "room_number": "INT-901",
            "name": "Integrity Test Room",
            "capacity": 50,
        },
    )

    # Directly invoke create with same room_number to test IntegrityError handling
    with pytest.raises(HTTPException) as exc_info:
        classroom_repository.create(
            db_session,
            {
                "room_number": "INT-901",
                "name": "Integrity Test Duplicate",
                "capacity": 60,
            },
        )

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail
