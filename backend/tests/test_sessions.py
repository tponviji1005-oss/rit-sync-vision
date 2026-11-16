"""
Integration and regression tests for Capture Session and Permit Management (/api/v1/sessions/*).
Includes tests for security remediations:
- SEC-SES-01: Hash permit tokens at rest (SHA-256) & permit rotation.
- SEC-SES-02: Authenticated permit validation endpoint.
- SEC-SES-03: Partial unique index preventing concurrent active classroom sessions.
- SEC-SES-04: Elimination of permit tokens from general session metadata responses.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import pytest
from fastapi import HTTPException

from backend.app.core.security import create_access_token
from backend.app.modules.classrooms.models import Classroom
from backend.app.modules.classrooms.repository import classroom_repository
from backend.app.modules.sessions.models import CapturePermit, CaptureSession, SessionStatus
from backend.app.modules.sessions.repository import hash_permit_token, session_repository
from backend.app.modules.sessions.service import session_service
from backend.app.modules.subjects.models import Subject
from backend.app.modules.subjects.repository import subject_repository
from backend.app.modules.users.models import UserRole
from backend.app.modules.users.schemas import UserCreate
from backend.app.modules.users.service import user_service


@pytest.fixture
def session_test_context(db_session):
    """Seed users (admin and two teachers), two classrooms, and a subject."""
    admin_name = "sess_admin"
    teacher1_name = "sess_teacher_1"
    teacher2_name = "sess_teacher_2"

    u_admin = user_service.get_by_username(db_session, admin_name)
    if not u_admin:
        u_admin = user_service.create_user(
            db_session,
            UserCreate(
                email="sess_admin@rit.edu",
                username=admin_name,
                full_name="Session Admin",
                password="AdminPassword123!",
                role=UserRole.ADMIN,
            ),
        )

    u_teacher1 = user_service.get_by_username(db_session, teacher1_name)
    if not u_teacher1:
        u_teacher1 = user_service.create_user(
            db_session,
            UserCreate(
                email="sess_t1@rit.edu",
                username=teacher1_name,
                full_name="Session Teacher 1",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    u_teacher2 = user_service.get_by_username(db_session, teacher2_name)
    if not u_teacher2:
        u_teacher2 = user_service.create_user(
            db_session,
            UserCreate(
                email="sess_t2@rit.edu",
                username=teacher2_name,
                full_name="Session Teacher 2",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    # Seed Classroom 1
    room = classroom_repository.get_by_room_number(db_session, "LH-SESS-1")
    if not room:
        room = classroom_repository.create(
            db_session,
            {
                "room_number": "LH-SESS-1",
                "name": "Session Hall 1",
                "capacity": 70,
                "camera_stream_url": "rtsp://camera.internal/session1",
                "is_active": True,
            },
        )

    # Seed Classroom 2
    room2 = classroom_repository.get_by_room_number(db_session, "LH-SESS-2")
    if not room2:
        room2 = classroom_repository.create(
            db_session,
            {
                "room_number": "LH-SESS-2",
                "name": "Session Hall 2",
                "capacity": 50,
                "camera_stream_url": "rtsp://camera.internal/session2",
                "is_active": True,
            },
        )

    # Seed Subject
    subj = subject_repository.get_by_subject_code(db_session, "SESS-CS101")
    if not subj:
        subj = subject_repository.create(
            db_session,
            {
                "subject_code": "SESS-CS101",
                "name": "Session Algorithms",
                "department": "Computer Science",
                "is_active": True,
            },
        )

    admin_token = create_access_token(data={"sub": admin_name, "role": "admin"})
    t1_token = create_access_token(data={"sub": teacher1_name, "role": "teacher"})
    t2_token = create_access_token(data={"sub": teacher2_name, "role": "teacher"})

    return {
        "admin": {"user": u_admin, "token": admin_token},
        "teacher1": {"user": u_teacher1, "token": t1_token},
        "teacher2": {"user": u_teacher2, "token": t2_token},
        "classroom1": room,
        "classroom2": room2,
        "subject": subj,
    }


def test_teacher_start_capture_session(client, session_test_context):
    """Verify Teacher can initialize an authorized capture session and receive a valid permit."""
    ctx = session_test_context
    token = ctx["teacher1"]["token"]

    resp = client.post(
        "/api/v1/sessions/",
        json={
            "classroom_id": ctx["classroom1"].id,
            "subject_id": ctx["subject"].id,
            "duration_minutes": 45,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ACTIVE"
    assert data["classroom_id"] == ctx["classroom1"].id
    assert data["subject_id"] == ctx["subject"].id
    assert data["teacher_id"] == ctx["teacher1"]["user"].id
    assert data["camera_stream_url"] == ctx["classroom1"].camera_stream_url
    assert "session_id" in data
    assert data["session_id"].startswith("SES-")

    # Verify active permit issuance
    permit = data["active_permit"]
    assert permit is not None
    assert permit["permit_id"].startswith("PERMIT-")
    assert permit["permit_token"] is not None
    assert permit["is_valid"] is True
    assert permit["classroom_id"] == ctx["classroom1"].id

    # Strictly verify no biometric or raw frame leaks
    assert "face_template" not in data
    assert "raw_frame" not in data


def test_session_fails_with_invalid_classroom_or_subject(client, session_test_context):
    """Verify starting a session with invalid foreign references fails with 404."""
    ctx = session_test_context
    token = ctx["teacher1"]["token"]

    # Nonexistent classroom
    resp1 = client.post(
        "/api/v1/sessions/",
        json={"classroom_id": 99999, "subject_id": ctx["subject"].id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 404
    assert "classroom" in resp1.json()["detail"].lower()

    # Nonexistent subject
    resp2 = client.post(
        "/api/v1/sessions/",
        json={"classroom_id": ctx["classroom1"].id, "subject_id": 99999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 404
    assert "subject" in resp2.json()["detail"].lower()


def test_prevent_overlapping_active_sessions_in_same_classroom(client, session_test_context):
    """SEC-SES-03: Verify attempting to start multiple overlapping sessions in the same room returns HTTP 409 Conflict."""
    ctx = session_test_context
    token = ctx["teacher1"]["token"]

    # Room 1 already has an active session from previous test
    resp = client.post(
        "/api/v1/sessions/",
        json={
            "classroom_id": ctx["classroom1"].id,
            "subject_id": ctx["subject"].id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409
    assert "already has an active capture session" in resp.json()["detail"]


def test_list_sessions_teacher_isolation_vs_admin(client, session_test_context):
    """Verify Teacher only sees their own sessions, while Admin can see all."""
    ctx = session_test_context

    # Teacher 2 starts session in Room 2
    t2_resp = client.post(
        "/api/v1/sessions/",
        json={
            "classroom_id": ctx["classroom2"].id,
            "subject_id": ctx["subject"].id,
        },
        headers={"Authorization": f"Bearer {ctx['teacher2']['token']}"},
    )
    assert t2_resp.status_code == 201

    # Teacher 1 listing
    t1_list = client.get(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['teacher1']['token']}"},
    )
    assert t1_list.status_code == 200
    for s in t1_list.json():
        assert s["teacher_id"] == ctx["teacher1"]["user"].id

    # Teacher 2 listing
    t2_list = client.get(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['teacher2']['token']}"},
    )
    assert t2_list.status_code == 200
    for s in t2_list.json():
        assert s["teacher_id"] == ctx["teacher2"]["user"].id

    # Admin listing sees sessions from both teachers
    admin_list = client.get(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['admin']['token']}"},
    )
    assert admin_list.status_code == 200
    teacher_ids = {s["teacher_id"] for s in admin_list.json()}
    assert ctx["teacher1"]["user"].id in teacher_ids
    assert ctx["teacher2"]["user"].id in teacher_ids


def test_teacher_cannot_access_or_modify_other_teacher_session(client, session_test_context):
    """Verify Teacher cannot view, complete, or cancel another teacher's capture session."""
    ctx = session_test_context
    t1_token = ctx["teacher1"]["token"]
    t2_token = ctx["teacher2"]["token"]

    # Teacher 1's session
    t1_sessions = client.get(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {t1_token}"},
    ).json()
    t1_session_id = t1_sessions[0]["session_id"]

    # Teacher 2 attempts GET -> 403 Forbidden
    resp_get = client.get(
        f"/api/v1/sessions/{t1_session_id}",
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert resp_get.status_code == 403
    assert "Access denied" in resp_get.json()["detail"]

    # Teacher 2 attempts POST complete -> 403 Forbidden
    resp_comp = client.post(
        f"/api/v1/sessions/{t1_session_id}/complete",
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert resp_comp.status_code == 403

    # Teacher 2 attempts POST cancel -> 403 Forbidden
    resp_canc = client.post(
        f"/api/v1/sessions/{t1_session_id}/cancel",
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert resp_canc.status_code == 403

    # Teacher 2 attempts GET permit -> 403 Forbidden
    resp_perm = client.get(
        f"/api/v1/sessions/{t1_session_id}/permit",
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert resp_perm.status_code == 403


def test_permit_validation_lifecycle(client, session_test_context):
    """Verify cryptographic permit validation and rejection of tampered tokens."""
    ctx = session_test_context
    t1_token = ctx["teacher1"]["token"]

    # Get Teacher 1's session permit via rotation/retrieval endpoint
    t1_session = client.get(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {t1_token}"},
    ).json()[0]

    permit_resp = client.get(
        f"/api/v1/sessions/{t1_session['session_id']}/permit",
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert permit_resp.status_code == 200
    permit_token = permit_resp.json()["permit_token"]

    # SEC-SES-02: Validate correct permit with authenticated header
    val_resp = client.post(
        "/api/v1/sessions/permit/validate",
        json={"permit_token": permit_token},
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True
    assert val_data["session_id"] == t1_session["session_id"]
    assert "authorized" in val_data["message"].lower()

    # Validate tampered token
    tampered_resp = client.post(
        "/api/v1/sessions/permit/validate",
        json={"permit_token": permit_token + "tampered_xyz"},
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert tampered_resp.status_code == 200
    assert tampered_resp.json()["valid"] is False


def test_session_completion_revokes_permit(client, session_test_context):
    """Verify completing a session marks it COMPLETED and revokes its permit."""
    ctx = session_test_context
    t1_token = ctx["teacher1"]["token"]

    t1_session = client.get(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {t1_token}"},
    ).json()[0]
    session_id = t1_session["session_id"]

    permit_token = client.get(
        f"/api/v1/sessions/{session_id}/permit",
        headers={"Authorization": f"Bearer {t1_token}"},
    ).json()["permit_token"]

    # Complete session
    comp_resp = client.post(
        f"/api/v1/sessions/{session_id}/complete",
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert comp_resp.status_code == 200
    data = comp_resp.json()
    assert data["status"] == "COMPLETED"
    assert data["end_time"] is not None

    # Cannot complete again
    comp_repeat = client.post(
        f"/api/v1/sessions/{session_id}/complete",
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert comp_repeat.status_code == 400

    # Permit is now invalidated
    val_resp = client.post(
        "/api/v1/sessions/permit/validate",
        json={"permit_token": permit_token},
        headers={"Authorization": f"Bearer {t1_token}"},
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["valid"] is False
    assert "no longer active" in val_resp.json()["message"] or "revoked" in val_resp.json()["message"]


def test_session_cancellation_revokes_permit(client, session_test_context):
    """Verify cancelling a session marks it CANCELLED and invalidates its permit."""
    ctx = session_test_context
    t2_token = ctx["teacher2"]["token"]

    t2_session = client.get(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {t2_token}"},
    ).json()[0]
    session_id = t2_session["session_id"]

    permit_token = client.get(
        f"/api/v1/sessions/{session_id}/permit",
        headers={"Authorization": f"Bearer {t2_token}"},
    ).json()["permit_token"]

    # Cancel session
    canc_resp = client.post(
        f"/api/v1/sessions/{session_id}/cancel",
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert canc_resp.status_code == 200
    assert canc_resp.json()["status"] == "CANCELLED"

    # Validate permit is revoked
    val_resp = client.post(
        "/api/v1/sessions/permit/validate",
        json={"permit_token": permit_token},
        headers={"Authorization": f"Bearer {t2_token}"},
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["valid"] is False


def test_expired_session_handling(db_session):
    """Verify sessions past their expiration timestamp are transitioned to EXPIRED."""
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    session_obj = session_repository.create_session(
        db_session,
        {
            "session_id": "SES-EXPIRED-TEST",
            "classroom_id": 991,
            "subject_id": 1,
            "teacher_id": 1,
            "status": SessionStatus.ACTIVE.value,
            "start_time": past - timedelta(hours=1),
            "expires_at": past,
        },
    )

    permit_token = create_access_token(
        data={"sub": "teacher", "session_id": session_obj.session_id, "scope": "camera_capture"},
        expires_delta=timedelta(minutes=-10),  # expired token
    )
    token_hash = hash_permit_token(permit_token)
    session_repository.create_permit(
        db_session,
        {
            "permit_id": "PERMIT-EXPIRED-TEST",
            "session_id": session_obj.id,
            "token_hash": token_hash,
            "issued_to_id": 1,
            "classroom_id": 991,
            "expires_at": past,
        },
    )

    val_resp = session_service.validate_permit(db_session, permit_token=permit_token)
    assert val_resp.valid is False


def test_unauthenticated_session_access_rejected(client):
    """Verify unauthenticated requests are rejected with 401."""
    resp1 = client.get("/api/v1/sessions/")
    assert resp1.status_code == 401

    resp2 = client.post("/api/v1/sessions/", json={"classroom_id": 1, "subject_id": 1})
    assert resp2.status_code == 401


# ============================================================================
# Security Remediation Regression Tests (SEC-SES-01 to SEC-SES-04)
# ============================================================================

def test_sec_ses_01_raw_tokens_never_stored_in_database(client, session_test_context, db_session):
    """SEC-SES-01: Verify raw permit tokens are never persisted in plaintext in the database."""
    ctx = session_test_context
    token = ctx["teacher1"]["token"]

    # Start session in a new classroom
    room_new = classroom_repository.create(
        db_session,
        {"room_number": "SEC-01-ROOM", "name": "Sec Room 1", "capacity": 30, "is_active": True},
    )

    resp = client.post(
        "/api/v1/sessions/",
        json={"classroom_id": room_new.id, "subject_id": ctx["subject"].id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    issued_token = resp.json()["active_permit"]["permit_token"]
    assert issued_token is not None

    # Inspect SQLite database directly
    cursor = db_session.connection.cursor()
    cursor.execute("SELECT token_hash FROM capture_permits WHERE session_id = ?", (resp.json()["id"],))
    rows = cursor.fetchall()
    assert len(rows) >= 1
    stored_hash = rows[0][0]

    # Verify the stored value is the 64-character SHA-256 hex string, NOT the raw JWT
    assert stored_hash != issued_token
    assert len(stored_hash) == 64
    assert stored_hash == hashlib.sha256(issued_token.strip().encode("utf-8")).hexdigest()


def test_sec_ses_01_permit_rotation_invalidates_previous_token(client, session_test_context, db_session):
    """SEC-SES-01: Verify rotating a permit invalidates the previous token while issuing a fresh one."""
    ctx = session_test_context
    token = ctx["teacher1"]["token"]

    room_rot = classroom_repository.create(
        db_session,
        {"room_number": "ROT-ROOM-1", "name": "Rotation Room", "capacity": 35, "is_active": True},
    )

    create_resp = client.post(
        "/api/v1/sessions/",
        json={"classroom_id": room_rot.id, "subject_id": ctx["subject"].id},
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = create_resp.json()["session_id"]
    token_1 = create_resp.json()["active_permit"]["permit_token"]

    # Validate token 1 is active
    val1 = client.post(
        "/api/v1/sessions/permit/validate",
        json={"permit_token": token_1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert val1.status_code == 200
    assert val1.json()["valid"] is True

    # Rotate/reissue permit via GET /permit
    rot_resp = client.get(
        f"/api/v1/sessions/{session_id}/permit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rot_resp.status_code == 200
    token_2 = rot_resp.json()["permit_token"]
    assert token_2 is not None
    assert token_2 != token_1

    # Verify previous token 1 is now rejected (revoked)
    val_old = client.post(
        "/api/v1/sessions/permit/validate",
        json={"permit_token": token_1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert val_old.status_code == 200
    assert val_old.json()["valid"] is False
    assert "revoked" in val_old.json()["message"]

    # Verify new token 2 is valid
    val_new = client.post(
        "/api/v1/sessions/permit/validate",
        json={"permit_token": token_2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert val_new.status_code == 200
    assert val_new.json()["valid"] is True


def test_sec_ses_02_anonymous_permit_validation_rejected_401(client, session_test_context):
    """SEC-SES-02: Verify anonymous callers cannot validate permits (HTTP 401 Unauthorized)."""
    resp = client.post(
        "/api/v1/sessions/permit/validate",
        json={"permit_token": "some_token"},
    )
    assert resp.status_code == 401


def test_sec_ses_03_concurrent_active_sessions_rejected_with_409(session_test_context, db_session):
    """SEC-SES-03: Verify partial unique index prevents concurrent active sessions in the same classroom."""
    ctx = session_test_context
    room_concurrent = classroom_repository.create(
        db_session,
        {"room_number": "CONCURR-101", "name": "Concurrency Room", "capacity": 40, "is_active": True},
    )

    # First active session created
    s1 = session_repository.create_session(
        db_session,
        {
            "session_id": "SES-CONCURR-1",
            "classroom_id": room_concurrent.id,
            "subject_id": ctx["subject"].id,
            "teacher_id": ctx["teacher1"]["user"].id,
            "status": "ACTIVE",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        },
    )
    assert s1.id is not None

    # Second active session directly inserted into the database for the same room
    with pytest.raises(HTTPException) as exc_info:
        session_repository.create_session(
            db_session,
            {
                "session_id": "SES-CONCURR-2",
                "classroom_id": room_concurrent.id,
                "subject_id": ctx["subject"].id,
                "teacher_id": ctx["teacher2"]["user"].id,
                "status": "ACTIVE",
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            },
        )
    assert exc_info.value.status_code == 409
    assert "already has an active capture session" in exc_info.value.detail


def test_sec_ses_03_new_session_allowed_after_previous_closed(client, session_test_context, db_session):
    """SEC-SES-03: Verify normal closed sessions do not prevent future active sessions in the same room."""
    ctx = session_test_context
    token = ctx["teacher1"]["token"]

    room_seq = classroom_repository.create(
        db_session,
        {"room_number": "SEQ-ROOM-1", "name": "Sequential Room", "capacity": 45, "is_active": True},
    )

    # Start and complete first session
    resp1 = client.post(
        "/api/v1/sessions/",
        json={"classroom_id": room_seq.id, "subject_id": ctx["subject"].id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 201
    s1_id = resp1.json()["session_id"]

    client.post(f"/api/v1/sessions/{s1_id}/complete", headers={"Authorization": f"Bearer {token}"})

    # Start second session in the same room -> must succeed!
    resp2 = client.post(
        "/api/v1/sessions/",
        json={"classroom_id": room_seq.id, "subject_id": ctx["subject"].id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 201
    assert resp2.json()["status"] == "ACTIVE"


def test_sec_ses_04_general_session_responses_do_not_expose_permit_tokens(client, session_test_context, db_session):
    """SEC-SES-04: Verify general GET session responses do not expose the raw permit token."""
    ctx = session_test_context
    token = ctx["teacher1"]["token"]

    room_exp = classroom_repository.create(
        db_session,
        {"room_number": "EXP-ROOM-1", "name": "Exposure Room", "capacity": 30, "is_active": True},
    )

    # Create session (token is returned only on creation)
    create_resp = client.post(
        "/api/v1/sessions/",
        json={"classroom_id": room_exp.id, "subject_id": ctx["subject"].id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]

    # General detail query: GET /api/v1/sessions/{id}
    detail_resp = client.get(
        f"/api/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["active_permit"] is not None
    assert detail_data["active_permit"]["permit_token"] is None  # Token omitted!

    # General list query: GET /api/v1/sessions/
    list_resp = client.get(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    for s in list_resp.json():
        if s["active_permit"] is not None:
            assert s["active_permit"]["permit_token"] is None
