"""
Integration and regression tests for Offline Synchronization (/api/v1/sync/*).
Tests core project principles from MANAGE.md §7:
1. Stable unique identifiers (event_id) for offline-queued events.
2. Idempotent processing: repeated delivery must never create duplicate attendance records.
3. Duplicate retries (e.g. after network failure) safely return DUPLICATE.
4. Idempotency collisions (same event_id, different payload) return CONFLICT.
5. Conflicts with teacher-finalized attendance records must be surfaced, never silently overwritten.
6. Role and session ownership authorization: teachers cannot sync attendance for sessions they do not own.
7. Partial batch resilience: invalid items in a batch receive REJECTED without rolling back valid items.
8. Unobserved students remain untouched (NOT_OBSERVED never automatically becomes ABSENT).
9. Server acknowledgement and status inspection endpoints.
"""

import uuid
import pytest
from datetime import datetime, timezone

from backend.app.core.security import create_access_token
from backend.app.modules.attendance.models import AttendanceStatus
from backend.app.modules.attendance.repository import attendance_repository
from backend.app.modules.classrooms.repository import classroom_repository
from backend.app.modules.sessions.models import SessionStatus
from backend.app.modules.sessions.repository import session_repository
from backend.app.modules.sessions.schemas import SessionCreate
from backend.app.modules.sessions.service import session_service
from backend.app.modules.students.repository import student_repository
from backend.app.modules.subjects.repository import subject_repository
from backend.app.modules.synchronization.models import SyncEventStatus
from backend.app.modules.synchronization.repository import sync_repository
from backend.app.modules.users.models import UserRole
from backend.app.modules.users.schemas import UserCreate
from backend.app.modules.users.service import user_service


@pytest.fixture
def sync_test_context(db_session):
    """Seed users, classrooms, subjects, students, and sessions specifically for offline sync tests."""
    admin_name = "sync_admin"
    teacher1_name = "sync_teacher_1"
    teacher2_name = "sync_teacher_2"

    u_admin = user_service.get_by_username(db_session, admin_name)
    if not u_admin:
        u_admin = user_service.create_user(
            db_session,
            UserCreate(
                email="sync_admin@rit.edu",
                username=admin_name,
                full_name="Sync Admin",
                password="AdminPassword123!",
                role=UserRole.ADMIN,
            ),
        )

    u_teacher1 = user_service.get_by_username(db_session, teacher1_name)
    if not u_teacher1:
        u_teacher1 = user_service.create_user(
            db_session,
            UserCreate(
                email="sync_t1@rit.edu",
                username=teacher1_name,
                full_name="Sync Teacher 1",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    u_teacher2 = user_service.get_by_username(db_session, teacher2_name)
    if not u_teacher2:
        u_teacher2 = user_service.create_user(
            db_session,
            UserCreate(
                email="sync_t2@rit.edu",
                username=teacher2_name,
                full_name="Sync Teacher 2",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    # Classrooms
    room1 = classroom_repository.get_by_room_number(db_session, "SYNC-ROOM-201")
    if not room1:
        room1 = classroom_repository.create(
            db_session,
            {
                "room_number": "SYNC-ROOM-201",
                "name": "Sync Room 201",
                "capacity": 50,
                "camera_stream_url": "rtsp://camera.internal/sync201",
                "is_active": True,
            },
        )

    room2 = classroom_repository.get_by_room_number(db_session, "SYNC-ROOM-202")
    if not room2:
        room2 = classroom_repository.create(
            db_session,
            {
                "room_number": "SYNC-ROOM-202",
                "name": "Sync Room 202",
                "capacity": 50,
                "camera_stream_url": "rtsp://camera.internal/sync202",
                "is_active": True,
            },
        )

    # Subject
    subj = subject_repository.get_by_subject_code(db_session, "SYNC-CS401")
    if not subj:
        subj = subject_repository.create(
            db_session,
            {
                "subject_code": "SYNC-CS401",
                "name": "Distributed Systems",
                "department": "Computer Science",
                "credits": 4,
                "is_active": True,
            },
        )

    # Students
    s1 = student_repository.get_by_student_id(db_session, "RIT2026SYNC001")
    if not s1:
        s1 = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026SYNC001",
                "first_name": "Alice",
                "last_name": "Sync",
                "email": "alice.sync@rit.edu",
                "is_active": True,
                "is_enrolled": True,
            },
        )

    s2 = student_repository.get_by_student_id(db_session, "RIT2026SYNC002")
    if not s2:
        s2 = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026SYNC002",
                "first_name": "Bob",
                "last_name": "Sync",
                "email": "bob.sync@rit.edu",
                "is_active": True,
                "is_enrolled": True,
            },
        )

    s3_inactive = student_repository.get_by_student_id(db_session, "RIT2026SYNC003")
    if not s3_inactive:
        s3_inactive = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026SYNC003",
                "first_name": "Inactive",
                "last_name": "Student",
                "email": "inactive.sync@rit.edu",
                "is_active": False,
                "is_enrolled": False,
            },
        )

    s4_unobserved = student_repository.get_by_student_id(db_session, "RIT2026SYNC004")
    if not s4_unobserved:
        s4_unobserved = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026SYNC004",
                "first_name": "Unobserved",
                "last_name": "Student",
                "email": "unobserved.sync@rit.edu",
                "is_active": True,
                "is_enrolled": True,
            },
        )

    # Teacher 1 Session
    sess1 = session_repository.get_active_session_in_classroom(db_session, room1.id)
    if not sess1:
        sess1 = session_service.create_session(
            db_session,
            SessionCreate(
                classroom_id=room1.id,
                subject_id=subj.id,
                camera_stream_url=room1.camera_stream_url,
                duration_minutes=60,
            ),
            current_user=u_teacher1,
        )

    # Teacher 2 Session
    sess2 = session_repository.get_active_session_in_classroom(db_session, room2.id)
    if not sess2:
        sess2 = session_service.create_session(
            db_session,
            SessionCreate(
                classroom_id=room2.id,
                subject_id=subj.id,
                camera_stream_url=room2.camera_stream_url,
                duration_minutes=60,
            ),
            current_user=u_teacher2,
        )

    admin_role = u_admin.role.value if hasattr(u_admin.role, "value") else str(u_admin.role)
    t1_role = u_teacher1.role.value if hasattr(u_teacher1.role, "value") else str(u_teacher1.role)
    t2_role = u_teacher2.role.value if hasattr(u_teacher2.role, "value") else str(u_teacher2.role)

    admin_token = create_access_token({"sub": u_admin.username, "role": admin_role})
    t1_token = create_access_token({"sub": u_teacher1.username, "role": t1_role})
    t2_token = create_access_token({"sub": u_teacher2.username, "role": t2_role})

    return {
        "admin": u_admin,
        "teacher1": u_teacher1,
        "teacher2": u_teacher2,
        "admin_token": admin_token,
        "t1_token": t1_token,
        "t2_token": t2_token,
        "classroom": room1,
        "classroom2": room2,
        "subject": subj,
        "session1": sess1,
        "session2": sess2,
        "student1": s1,
        "student2": s2,
        "student_inactive": s3_inactive,
        "student_unobserved": s4_unobserved,
    }


def _start_fresh_session(client, db_session, classroom, subject, teacher_token):
    """Ensure no active session in classroom and start a clean session."""
    active = session_repository.get_active_session_in_classroom(db_session, classroom.id)
    if active:
        session_repository.update_status(db_session, session=active, new_status=SessionStatus.COMPLETED.value)

    resp = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "classroom_id": classroom.id,
            "subject_id": subject.id,
            "duration_minutes": 60,
        },
    )
    assert resp.status_code == 201
    return resp.json()["session_id"]


def test_sync_status_endpoint(client):
    """Test health and status check for offline synchronization module."""
    resp = client.get("/api/v1/sync/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["module"] == "synchronization"


def test_successful_offline_synchronization(client, sync_test_context, db_session):
    """
    Test successful batch submission of offline attendance events.
    Verifies that attendance records and sync audit events are created.
    """
    ctx = sync_test_context
    session_id = ctx["session1"].session_id
    t1_token = ctx["t1_token"]

    event1_id = f"evt-{uuid.uuid4()}"
    event2_id = f"evt-{uuid.uuid4()}"

    batch_payload = {
        "events": [
            {
                "event_id": event1_id,
                "session_id": session_id,
                "student_id": "RIT2026SYNC001",
                "event_type": "RECORD_ATTENDANCE",
                "status": "PRESENT",
                "notes": "Offline scanned badge",
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "event_id": event2_id,
                "session_id": session_id,
                "student_id": "RIT2026SYNC002",
                "event_type": "RECORD_ATTENDANCE",
                "status": "ABSENT",
                "notes": "Teacher noted absence offline",
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]
    }

    resp = client.post(
        "/api/v1/sync/attendance",
        json=batch_payload,
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_events"] == 2
    assert data["synced_count"] == 2
    assert data["duplicate_count"] == 0
    assert data["conflict_count"] == 0
    assert data["rejected_count"] == 0

    results = data["results"]
    assert len(results) == 2
    assert results[0]["event_id"] == event1_id
    assert results[0]["status"] == SyncEventStatus.SYNCED.value
    assert results[0]["attendance_record_id"] is not None

    assert results[1]["event_id"] == event2_id
    assert results[1]["status"] == SyncEventStatus.SYNCED.value
    assert results[1]["attendance_record_id"] is not None

    # Verify database state
    rec1 = attendance_repository.get_by_id(db_session, results[0]["attendance_record_id"])
    assert rec1 is not None
    assert rec1.student_institutional_id == "RIT2026SYNC001"
    assert rec1.status == "PRESENT"
    assert rec1.is_finalized is True
    assert rec1.source == "OFFLINE_SYNC"

    rec2 = attendance_repository.get_by_id(db_session, results[1]["attendance_record_id"])
    assert rec2 is not None
    assert rec2.student_institutional_id == "RIT2026SYNC002"
    assert rec2.status == "ABSENT"
    assert rec2.is_finalized is True
    assert rec2.source == "OFFLINE_SYNC"

    # Verify sync_events table records
    sync_evt1 = sync_repository.get_by_event_id(db_session, event1_id)
    assert sync_evt1 is not None
    assert sync_evt1.sync_status == SyncEventStatus.SYNCED.value


def test_repeated_operation_same_idempotency_identifier_duplicate(client, sync_test_context, db_session):
    """
    Test idempotency: submitting the exact same batch again must return DUPLICATE
    and must NOT create duplicate attendance records.
    """
    ctx = sync_test_context
    t1_token = ctx["t1_token"]
    session_id = _start_fresh_session(client, db_session, ctx["classroom"], ctx["subject"], t1_token)

    event_id = f"evt-{uuid.uuid4()}"
    batch_payload = {
        "events": [
            {
                "event_id": event_id,
                "session_id": session_id,
                "student_id": "RIT2026SYNC001",
                "event_type": "RECORD_ATTENDANCE",
                "status": "PRESENT",
                "notes": "First attempt",
            }
        ]
    }

    # Initial submission
    res1 = client.post(
        "/api/v1/sync/attendance",
        json=batch_payload,
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res1.status_code == 200
    assert res1.json()["synced_count"] == 1
    first_record_id = res1.json()["results"][0]["attendance_record_id"]

    # Repeated submission with the exact same event_id and payload
    res2 = client.post(
        "/api/v1/sync/attendance",
        json=batch_payload,
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total_events"] == 1
    assert data2["synced_count"] == 0
    assert data2["duplicate_count"] == 1
    assert data2["conflict_count"] == 0
    assert data2["rejected_count"] == 0

    assert data2["results"][0]["event_id"] == event_id
    assert data2["results"][0]["status"] == SyncEventStatus.DUPLICATE.value
    # Returns the existing record ID without duplicating
    assert data2["results"][0]["attendance_record_id"] == first_record_id


def test_duplicate_retry_after_simulated_network_failure(client, sync_test_context, db_session):
    """
    Simulate a client that submits an event, experiences network timeout before receiving
    the acknowledgement, and resubmits the queued event.
    """
    ctx = sync_test_context
    t1_token = ctx["t1_token"]
    session_id = _start_fresh_session(client, db_session, ctx["classroom"], ctx["subject"], t1_token)

    retry_event_id = f"evt-net-retry-{uuid.uuid4()}"
    payload = {
        "events": [
            {
                "event_id": retry_event_id,
                "session_id": session_id,
                "student_id": "RIT2026SYNC002",
                "event_type": "RECORD_ATTENDANCE",
                "status": "PRESENT",
                "notes": "Network retry event",
            }
        ]
    }

    # First attempt: successfully reaches server and persists
    res1 = client.post("/api/v1/sync/attendance", json=payload, headers={"Authorization": f"Bearer {t1_token}"})
    assert res1.status_code == 200
    assert res1.json()["synced_count"] == 1
    rec_id = res1.json()["results"][0]["attendance_record_id"]

    # Client retries because it didn't get confirmation
    res2 = client.post("/api/v1/sync/attendance", json=payload, headers={"Authorization": f"Bearer {t1_token}"})
    assert res2.status_code == 200
    assert res2.json()["duplicate_count"] == 1
    assert res2.json()["results"][0]["status"] == SyncEventStatus.DUPLICATE.value
    assert res2.json()["results"][0]["attendance_record_id"] == rec_id


def test_same_identifier_different_payload_conflict(client, sync_test_context, db_session):
    """
    Test idempotency violation: reusing an existing event_id with differing payload data
    must be flagged as a CONFLICT and rejected from altering state.
    """
    ctx = sync_test_context
    t1_token = ctx["t1_token"]
    session_id = _start_fresh_session(client, db_session, ctx["classroom"], ctx["subject"], t1_token)

    collision_event_id = f"evt-collision-{uuid.uuid4()}"

    # Step 1: Submit original event
    res1 = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": collision_event_id,
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC001",
                    "event_type": "RECORD_ATTENDANCE",
                    "status": "PRESENT",
                    "notes": "Original payload",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res1.status_code == 200
    assert res1.json()["synced_count"] == 1

    # Step 2: Attempt to reuse the SAME event_id with DIFFERENT payload (status ABSENT instead of PRESENT)
    res2 = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": collision_event_id,
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC001",
                    "event_type": "RECORD_ATTENDANCE",
                    "status": "ABSENT",  # CHANGED STATUS!
                    "notes": "Altered payload with same event_id",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["conflict_count"] == 1
    assert data2["synced_count"] == 0
    assert data2["results"][0]["status"] == SyncEventStatus.CONFLICT.value
    assert "conflict" in data2["results"][0]["message"].lower()


def test_invalid_and_cancelled_session_rejected(client, sync_test_context, db_session):
    """Test that events referencing nonexistent or cancelled sessions receive REJECTED."""
    ctx = sync_test_context
    t1_token = ctx["t1_token"]

    # 1. Nonexistent session
    res1 = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": f"evt-{uuid.uuid4()}",
                    "session_id": "NON-EXISTENT-SESSION-9999",
                    "student_id": "RIT2026SYNC001",
                    "status": "PRESENT",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res1.status_code == 200
    assert res1.json()["rejected_count"] == 1
    assert "not found" in res1.json()["results"][0]["message"].lower()

    # 2. Cancelled session
    room_cancel = classroom_repository.get_by_room_number(db_session, "SYNC-ROOM-CANCEL")
    if not room_cancel:
        room_cancel = classroom_repository.create(
            db_session,
            {
                "room_number": "SYNC-ROOM-CANCEL",
                "name": "Sync Cancel Room",
                "capacity": 30,
                "is_active": True,
            },
        )
    cancelled_sess = session_service.create_session(
        db_session,
        SessionCreate(
            classroom_id=room_cancel.id,
            subject_id=ctx["session1"].subject_id,
            duration_minutes=30,
        ),
        current_user=ctx["teacher1"],
    )
    session_service.cancel_session(db_session, cancelled_sess.session_id, current_user=ctx["teacher1"])

    res2 = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": f"evt-{uuid.uuid4()}",
                    "session_id": cancelled_sess.session_id,
                    "student_id": "RIT2026SYNC001",
                    "status": "PRESENT",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res2.status_code == 200
    assert res2.json()["rejected_count"] == 1
    assert "cancelled" in res2.json()["results"][0]["message"].lower()


def test_unauthorized_user_and_cross_teacher_access(client, sync_test_context):
    """
    Test authorization rules:
    - Unauthenticated callers are rejected with 401.
    - Teacher 2 cannot sync attendance for Teacher 1's session (event receives REJECTED).
    - Administrator can sync attendance for any session.
    """
    ctx = sync_test_context
    session1_id = ctx["session1"].session_id
    t2_token = ctx["t2_token"]
    admin_token = ctx["admin_token"]

    event_unauth = {
        "events": [
            {
                "event_id": f"evt-{uuid.uuid4()}",
                "session_id": session1_id,
                "student_id": "RIT2026SYNC001",
                "status": "PRESENT",
            }
        ]
    }

    # 1. Unauthenticated -> 401 Unauthorized
    res_no_auth = client.post("/api/v1/sync/attendance", json=event_unauth)
    assert res_no_auth.status_code == 401

    # 2. Teacher 2 syncing for Teacher 1's session -> REJECTED
    res_cross = client.post(
        "/api/v1/sync/attendance",
        json=event_unauth,
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert res_cross.status_code == 200
    assert res_cross.json()["rejected_count"] == 1
    assert "unauthorized" in res_cross.json()["results"][0]["message"].lower()

    # 3. Administrator syncing for Teacher 1's session -> ALLOWED
    admin_event_id = f"evt-admin-{uuid.uuid4()}"
    res_admin = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": admin_event_id,
                    "session_id": session1_id,
                    "student_id": "RIT2026SYNC001",
                    "status": "PRESENT",
                }
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 200
    # Note: student1 was already finalized PRESENT in previous test, so duplicate or synced is expected
    assert res_admin.json()["rejected_count"] == 0


def test_invalid_and_inactive_student_reference(client, sync_test_context):
    """Test that events referencing nonexistent or inactive students are REJECTED."""
    ctx = sync_test_context
    session_id = ctx["session1"].session_id
    t1_token = ctx["t1_token"]

    # 1. Nonexistent student
    res1 = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": f"evt-{uuid.uuid4()}",
                    "session_id": session_id,
                    "student_id": "RIT9999UNKNOWN",
                    "status": "PRESENT",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res1.status_code == 200
    assert res1.json()["rejected_count"] == 1
    assert "not found" in res1.json()["results"][0]["message"].lower()

    # 2. Inactive student
    res2 = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": f"evt-{uuid.uuid4()}",
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC003",  # Inactive
                    "status": "PRESENT",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res2.status_code == 200
    assert res2.json()["rejected_count"] == 1
    assert "inactive" in res2.json()["results"][0]["message"].lower()


def test_partially_valid_batch(client, sync_test_context):
    """
    Test partial batch resilience:
    A batch containing 1 valid event, 1 invalid student event, 1 invalid status event,
    and 1 duplicate event must process each item correctly without rolling back the valid ones.
    """
    ctx = sync_test_context
    session_id = ctx["session2"].session_id
    t2_token = ctx["t2_token"]

    valid_event_id = f"evt-valid-{uuid.uuid4()}"
    duplicate_seed_id = f"evt-dup-seed-{uuid.uuid4()}"

    # Pre-seed one event to test duplicate recognition
    client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": duplicate_seed_id,
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC002",
                    "status": "PRESENT",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t2_token}"},
    )

    batch_payload = {
        "events": [
            # Item 1: Valid
            {
                "event_id": valid_event_id,
                "session_id": session_id,
                "student_id": "RIT2026SYNC001",
                "status": "PRESENT",
            },
            # Item 2: Unknown student -> REJECTED
            {
                "event_id": f"evt-bad-stud-{uuid.uuid4()}",
                "session_id": session_id,
                "student_id": "RIT9999NOTREAL",
                "status": "PRESENT",
            },
            # Item 3: Invalid status -> REJECTED
            {
                "event_id": f"evt-bad-status-{uuid.uuid4()}",
                "session_id": session_id,
                "student_id": "RIT2026SYNC001",
                "status": "INVALID_STATUS_CODE",
            },
            # Item 4: Duplicate of pre-seeded event -> DUPLICATE
            {
                "event_id": duplicate_seed_id,
                "session_id": session_id,
                "student_id": "RIT2026SYNC002",
                "status": "PRESENT",
            },
        ]
    }

    resp = client.post(
        "/api/v1/sync/attendance",
        json=batch_payload,
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_events"] == 4
    assert data["synced_count"] == 1
    assert data["duplicate_count"] == 1
    assert data["rejected_count"] == 2
    assert data["conflict_count"] == 0

    results = data["results"]
    assert results[0]["event_id"] == valid_event_id
    assert results[0]["status"] == SyncEventStatus.SYNCED.value

    assert results[1]["status"] == SyncEventStatus.REJECTED.value
    assert results[2]["status"] == SyncEventStatus.REJECTED.value
    assert results[3]["status"] == SyncEventStatus.DUPLICATE.value


def test_teacher_finalized_attendance_conflict(client, sync_test_context, db_session):
    """
    MANAGE.md §7: "Conflicts must be surfaced for resolution; never silently overwrite a teacher-finalized record."
    If a student's attendance is already finalized as ABSENT, an offline sync event claiming PRESENT
    must surface as CONFLICT and MUST NOT overwrite the finalized ABSENT record.
    """
    ctx = sync_test_context
    t2_token = ctx["t2_token"]
    session_id = _start_fresh_session(client, db_session, ctx["classroom2"], ctx["subject"], t2_token)
    sess2_obj = session_repository.get_by_session_id(db_session, session_id)
    student1_obj = ctx["student1"]

    # Explicitly finalize student1 as ABSENT in session2
    rec = attendance_repository.get_by_session_and_student(db_session, sess2_obj.id, student1_obj.id)
    if rec:
        attendance_repository.update(
            db_session,
            rec,
            {
                "status": "ABSENT",
                "is_finalized": True,
                "finalized_by_id": ctx["teacher2"].id,
                "notes": "Teacher verified physical absence",
            },
        )
    else:
        rec = attendance_repository.create(
            db_session,
            {
                "session_id": sess2_obj.id,
                "session_code": sess2_obj.session_id,
                "student_id": student1_obj.id,
                "student_institutional_id": student1_obj.student_id,
                "status": "ABSENT",
                "is_finalized": True,
                "source": "TEACHER_MANUAL",
                "finalized_by_id": ctx["teacher2"].id,
                "notes": "Teacher verified physical absence",
            },
        )

    conflict_event_id = f"evt-conflict-{uuid.uuid4()}"
    resp = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": conflict_event_id,
                    "session_id": session_id,
                    "student_id": student1_obj.student_id,
                    "status": "PRESENT",  # Conflicts with teacher's finalized ABSENT decision!
                    "notes": "Offline scanner logged student as present",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["conflict_count"] == 1
    assert data["synced_count"] == 0
    assert data["results"][0]["status"] == SyncEventStatus.CONFLICT.value
    assert "conflict" in data["results"][0]["message"].lower()

    # CRITICAL: Verify the finalized record was NOT overwritten!
    preserved_rec = attendance_repository.get_by_id(db_session, rec.id)
    assert preserved_rec.status == "ABSENT"
    assert preserved_rec.is_finalized is True


def test_unobserved_students_remain_not_observed(client, sync_test_context, db_session):
    """
    MANAGE.md §5: "NOT_OBSERVED must NEVER automatically become ABSENT."
    Syncing attendance events for some students must not alter or infer ABSENT
    for students who were unobserved and not in the batch.
    """
    ctx = sync_test_context
    session_id = ctx["session1"].session_id
    t1_token = ctx["t1_token"]

    # Student 4 (RIT2026SYNC004) was never mentioned in any sync batch
    s4 = ctx["student_unobserved"]

    # Run a sync batch for student 1 only
    client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": f"evt-single-{uuid.uuid4()}",
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC001",
                    "status": "PRESENT",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )

    # Verify that no record was created for student 4 (remains not observed)
    s4_rec = attendance_repository.get_by_session_and_student(db_session, ctx["session1"].id, s4.id)
    assert s4_rec is None or s4_rec.status == AttendanceStatus.NOT_OBSERVED.value


def test_get_sync_events_by_id_and_session(client, sync_test_context):
    """
    Test inspecting sync events:
    - GET /api/v1/sync/events/{event_id}
    - GET /api/v1/sync/sessions/{session_id}/events
    - Access isolation: Teacher cannot inspect events for sessions they do not own.
    """
    ctx = sync_test_context
    session_id = ctx["session1"].session_id
    t1_token = ctx["t1_token"]
    t2_token = ctx["t2_token"]

    event_id = f"evt-inspect-{uuid.uuid4()}"
    client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": event_id,
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC001",
                    "status": "PRESENT",
                    "notes": "Inspection test event",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )

    # 1. Fetch by event_id as session owner (Teacher 1) -> 200 OK
    res_single = client.get(
        f"/api/v1/sync/events/{event_id}",
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res_single.status_code == 200
    evt_data = res_single.json()
    assert evt_data["event_id"] == event_id
    assert evt_data["sync_status"] in (SyncEventStatus.SYNCED.value, SyncEventStatus.DUPLICATE.value)

    # 2. Fetch by event_id as non-owner (Teacher 2) -> 403 Forbidden
    res_forbidden = client.get(
        f"/api/v1/sync/events/{event_id}",
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert res_forbidden.status_code == 403

    # 3. List by session as session owner -> 200 OK
    res_list = client.get(
        f"/api/v1/sync/sessions/{session_id}/events",
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res_list.status_code == 200
    events_list = res_list.json()
    assert isinstance(events_list, list)
    assert len(events_list) >= 1

    # 4. List by session as non-owner (Teacher 2) -> 403 Forbidden
    res_list_forbidden = client.get(
        f"/api/v1/sync/sessions/{session_id}/events",
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert res_list_forbidden.status_code == 403


def test_transaction_rollback_and_graceful_recovery_on_error(client, sync_test_context, db_session, monkeypatch):
    """
    Test transaction rollback resilience:
    When an unexpected database write error occurs while creating a sync event,
    the transaction is rolled back, the error is caught safely, and the failing item
    is recorded as REJECTED without crashing the entire batch request.
    """
    ctx = sync_test_context
    t1_token = ctx["t1_token"]
    session_id = _start_fresh_session(client, db_session, ctx["classroom"], ctx["subject"], t1_token)

    failing_event_id = f"evt-fail-{uuid.uuid4()}"
    valid_event_id = f"evt-good-{uuid.uuid4()}"

    original_create = sync_repository.create

    def mock_create(db, event_data):
        if event_data.get("event_id") == failing_event_id:
            raise RuntimeError("Simulated transient database write failure")
        return original_create(db, event_data)

    monkeypatch.setattr(sync_repository, "create", mock_create)

    resp = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": failing_event_id,
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC001",
                    "status": "PRESENT",
                },
                {
                    "event_id": valid_event_id,
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC002",
                    "status": "ABSENT",
                },
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_events"] == 2
    assert data["rejected_count"] == 1
    assert data["synced_count"] == 1

    results = data["results"]
    assert results[0]["event_id"] == failing_event_id
    assert results[0]["status"] == SyncEventStatus.REJECTED.value
    assert "Simulated transient database write failure" in results[0]["message"]

    assert results[1]["event_id"] == valid_event_id
    assert results[1]["status"] == SyncEventStatus.SYNCED.value


def test_concurrent_duplicate_resolution(client, sync_test_context, db_session, monkeypatch):
    """
    Test simulated concurrent race condition:
    Two threads attempt to synchronize the same event_id at the same instant.
    The second thread hits a unique constraint HTTP 409 conflict upon insertion,
    which is caught and re-evaluated to DUPLICATE without failing.
    """
    ctx = sync_test_context
    t1_token = ctx["t1_token"]
    session_id = _start_fresh_session(client, db_session, ctx["classroom"], ctx["subject"], t1_token)

    event_id = f"evt-race-{uuid.uuid4()}"

    # Step 1: Pre-populate the sync event to simulate another concurrent thread having just written it
    res1 = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": event_id,
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC001",
                    "status": "PRESENT",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res1.status_code == 200
    assert res1.json()["synced_count"] == 1

    # Step 2: Now simulate a race where get_by_event_id returned None initially,
    # but sync_repository.create raises 409 conflict because row exists
    from fastapi import HTTPException

    def mock_get_by_event_id_race(db, eid):
        # Pretend it wasn't found in step 1 lookup
        return None

    original_get = sync_repository.get_by_event_id
    monkeypatch.setattr(sync_repository, "get_by_event_id", mock_get_by_event_id_race)

    def mock_create_conflict(db, event_data):
        # Now restore original get so re-check finds it, and raise 409
        monkeypatch.setattr(sync_repository, "get_by_event_id", original_get)
        raise HTTPException(status_code=409, detail="Duplicate key on event_id")

    monkeypatch.setattr(sync_repository, "create", mock_create_conflict)

    res2 = client.post(
        "/api/v1/sync/attendance",
        json={
            "events": [
                {
                    "event_id": event_id,
                    "session_id": session_id,
                    "student_id": "RIT2026SYNC001",
                    "status": "PRESENT",
                }
            ]
        },
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert res2.status_code == 200
    assert res2.json()["duplicate_count"] == 1
    assert res2.json()["results"][0]["status"] == SyncEventStatus.DUPLICATE.value
    assert "concurrent resolution" in res2.json()["results"][0]["message"]

