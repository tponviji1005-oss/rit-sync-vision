"""
Integration and regression tests for Attendance Management (/api/v1/attendance/*).
Tests core project principles from MANAGE.md §5 & §6:
1. AI observations propose candidate records and NEVER directly finalize attendance.
2. NOT_OBSERVED never automatically becomes ABSENT.
3. Only authorized teachers/admins can finalize or modify attendance.
4. Duplicate records for the same session and student are prevented (409 Conflict).
5. Non-biometric manual attendance option for teachers.
6. Audit trail is strictly maintained on modifications (previous_status, notes, finalized_by_id).
7. Cross-teacher session access isolation (403 Forbidden).
8. Token-based authentication enforcement (401 Unauthorized).
"""

import pytest

from backend.app.core.security import create_access_token
from backend.app.modules.attendance.models import AttendanceStatus
from backend.app.modules.attendance.repository import attendance_repository
from backend.app.modules.classrooms.repository import classroom_repository
from backend.app.modules.sessions.repository import session_repository
from backend.app.modules.sessions.schemas import SessionCreate
from backend.app.modules.sessions.service import session_service
from backend.app.modules.students.repository import student_repository
from backend.app.modules.subjects.repository import subject_repository
from backend.app.modules.users.models import UserRole
from backend.app.modules.users.schemas import UserCreate
from backend.app.modules.users.service import user_service


@pytest.fixture
def attendance_test_context(db_session):
    """Seed users, classrooms, subjects, students, and active sessions for attendance tests."""
    admin_name = "att_admin"
    teacher1_name = "att_teacher_1"
    teacher2_name = "att_teacher_2"

    u_admin = user_service.get_by_username(db_session, admin_name)
    if not u_admin:
        u_admin = user_service.create_user(
            db_session,
            UserCreate(
                email="att_admin@rit.edu",
                username=admin_name,
                full_name="Attendance Admin",
                password="AdminPassword123!",
                role=UserRole.ADMIN,
            ),
        )

    u_teacher1 = user_service.get_by_username(db_session, teacher1_name)
    if not u_teacher1:
        u_teacher1 = user_service.create_user(
            db_session,
            UserCreate(
                email="att_t1@rit.edu",
                username=teacher1_name,
                full_name="Attendance Teacher 1",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    u_teacher2 = user_service.get_by_username(db_session, teacher2_name)
    if not u_teacher2:
        u_teacher2 = user_service.create_user(
            db_session,
            UserCreate(
                email="att_t2@rit.edu",
                username=teacher2_name,
                full_name="Attendance Teacher 2",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    # Seed Classroom
    room = classroom_repository.get_by_room_number(db_session, "ATT-ROOM-101")
    if not room:
        room = classroom_repository.create(
            db_session,
            {
                "room_number": "ATT-ROOM-101",
                "name": "Vision Lab 101",
                "capacity": 60,
                "camera_stream_url": "rtsp://camera.internal/att101",
                "is_active": True,
            },
        )

    # Seed Classroom 2 for Teacher 2
    room2 = classroom_repository.get_by_room_number(db_session, "ATT-ROOM-102")
    if not room2:
        room2 = classroom_repository.create(
            db_session,
            {
                "room_number": "ATT-ROOM-102",
                "name": "Vision Lab 102",
                "capacity": 45,
                "camera_stream_url": "rtsp://camera.internal/att102",
                "is_active": True,
            },
        )

    # Seed Subject
    subj = subject_repository.get_by_subject_code(db_session, "ATT-CS301")
    if not subj:
        subj = subject_repository.create(
            db_session,
            {
                "subject_code": "ATT-CS301",
                "name": "Computer Vision & ML",
                "department": "Computer Science",
                "credits": 4,
                "is_active": True,
            },
        )

    # Seed Students with unique IDs that do not clash with test_students.py
    s1 = student_repository.get_by_student_id(db_session, "RIT2026ATT001")
    if not s1:
        s1 = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026ATT001",
                "first_name": "Arun",
                "last_name": "Kumar",
                "email": "arun.att@rit.edu",
                "is_active": True,
                "is_enrolled": True,
            },
        )

    s2 = student_repository.get_by_student_id(db_session, "RIT2026ATT002")
    if not s2:
        s2 = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026ATT002",
                "first_name": "Bhavna",
                "last_name": "Sharma",
                "email": "bhavna.att@rit.edu",
                "is_active": True,
                "is_enrolled": True,
            },
        )

    s3 = student_repository.get_by_student_id(db_session, "RIT2026ATT003")
    if not s3:
        s3 = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026ATT003",
                "first_name": "Chitra",
                "last_name": "Raman",
                "email": "chitra.att@rit.edu",
                "is_active": True,
                "is_enrolled": True,
            },
        )

    admin_token = create_access_token(data={"sub": admin_name, "role": "admin"})
    t1_token = create_access_token(data={"sub": teacher1_name, "role": "teacher"})
    t2_token = create_access_token(data={"sub": teacher2_name, "role": "teacher"})

    return {
        "admin": u_admin,
        "teacher1": u_teacher1,
        "teacher2": u_teacher2,
        "admin_token": admin_token,
        "t1_token": t1_token,
        "t2_token": t2_token,
        "classroom": room,
        "classroom2": room2,
        "subject": subj,
        "students": [s1, s2, s3],
    }


def _ensure_no_active_session(db_session, classroom_id):
    active = session_repository.get_active_session_in_classroom(db_session, classroom_id=classroom_id)
    if active:
        session_repository.update_status(db_session, session=active, new_status="COMPLETED")


def test_ai_proposals_creates_unfinalized_candidates(client, db_session, attendance_test_context):
    """
    Verify AI observations create candidate proposals without finalization:
    - MATCHED becomes PRESENT_CANDIDATE (is_finalized=False).
    - NEEDS_REVIEW/INSUFFICIENT_QUALITY becomes NEEDS_REVIEW (is_finalized=False).
    - AI observations NEVER set is_finalized to True.
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    # Start session
    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    assert ses_res.status_code == 201
    session_code = ses_res.json()["session_id"]

    # Submit AI proposals
    proposals_payload = {
        "observations": [
            {
                "track_id": "track_101",
                "candidate_student_id": "RIT2026ATT001",
                "match_state": "MATCHED",
                "confidence": 0.94,
                "evidence_count": 6,
            },
            {
                "track_id": "track_102",
                "candidate_student_id": "RIT2026ATT002",
                "match_state": "NEEDS_REVIEW",
                "confidence": 0.58,
                "evidence_count": 2,
            },
        ]
    }
    prop_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers_t1,
        json=proposals_payload,
    )
    assert prop_res.status_code == 200
    records = prop_res.json()
    assert len(records) == 2

    r1 = next(r for r in records if r["student_institutional_id"] == "RIT2026ATT001")
    assert r1["status"] == AttendanceStatus.PRESENT_CANDIDATE.value
    assert r1["is_finalized"] is False
    assert r1["source"] == "AI_PROPOSAL"
    assert r1["confidence"] == 0.94

    r2 = next(r for r in records if r["student_institutional_id"] == "RIT2026ATT002")
    assert r2["status"] == AttendanceStatus.NEEDS_REVIEW.value
    assert r2["is_finalized"] is False
    assert r2["source"] == "AI_PROPOSAL"


def test_not_observed_never_automatically_becomes_absent(client, db_session, attendance_test_context):
    """
    CRITICAL PROJECT RULE: NOT_OBSERVED must NEVER automatically become ABSENT.
    When a session has enrolled students without observation, the review summary
    reports them as NOT_OBSERVED with is_finalized=False, NOT as ABSENT.
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    assert ses_res.status_code == 201
    session_code = ses_res.json()["session_id"]

    # Only observe RIT2026ATT001; RIT2026ATT002 and RIT2026ATT003 are NOT observed
    client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers_t1,
        json={
            "observations": [
                {
                    "track_id": "track_1",
                    "candidate_student_id": "RIT2026ATT001",
                    "match_state": "MATCHED",
                    "confidence": 0.92,
                }
            ]
        },
    )

    # Get session attendance review
    rev_res = client.get(f"/api/v1/attendance/sessions/{session_code}", headers=headers_t1)
    assert rev_res.status_code == 200
    data = rev_res.json()

    assert data["session_code"] == session_code
    assert data["present_candidates"] >= 1
    assert data["not_observed"] >= 2
    assert data["finalized_absent"] == 0

    # Ensure unobserved student RIT2026ATT003 is NOT_OBSERVED, not ABSENT
    rec_s3 = next(r for r in data["records"] if r["student_institutional_id"] == "RIT2026ATT003")
    assert rec_s3["status"] == AttendanceStatus.NOT_OBSERVED.value
    assert rec_s3["is_finalized"] is False
    assert rec_s3["status"] != AttendanceStatus.ABSENT.value


def test_teacher_batch_finalization_present_and_absent(client, db_session, attendance_test_context):
    """
    Verify teacher finalizes session attendance:
    - Only PRESENT and ABSENT are allowed as finalized statuses.
    - Transitions records to is_finalized=True and stamps finalized_by_id and finalized_at.
    - Rejects invalid finalization attempts (e.g. attempting to finalize as NOT_OBSERVED).
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    # Teacher finalizes: RIT2026ATT001 as PRESENT, RIT2026ATT002 as ABSENT
    finalize_payload = {
        "decisions": [
            {"student_id": "RIT2026ATT001", "status": "PRESENT", "notes": "Verified by teacher"},
            {"student_id": "RIT2026ATT002", "status": "ABSENT", "notes": "Confirmed absent by teacher"},
        ]
    }
    fin_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/finalize",
        headers=headers_t1,
        json=finalize_payload,
    )
    assert fin_res.status_code == 200
    finalized = fin_res.json()
    assert len(finalized) == 2

    f1 = next(r for r in finalized if r["student_institutional_id"] == "RIT2026ATT001")
    assert f1["status"] == AttendanceStatus.PRESENT.value
    assert f1["is_finalized"] is True
    assert f1["finalized_by_id"] == ctx["teacher1"].id
    assert f1["finalized_at"] is not None

    f2 = next(r for r in finalized if r["student_institutional_id"] == "RIT2026ATT002")
    assert f2["status"] == AttendanceStatus.ABSENT.value
    assert f2["is_finalized"] is True
    assert f2["finalized_by_id"] == ctx["teacher1"].id

    # Reject invalid finalization status
    invalid_payload = {
        "decisions": [
            {"student_id": "RIT2026ATT003", "status": "NOT_OBSERVED"}
        ]
    }
    inv_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/finalize",
        headers=headers_t1,
        json=invalid_payload,
    )
    assert inv_res.status_code == 400
    assert "Only PRESENT or ABSENT can be finalized" in inv_res.json()["detail"]


def test_ai_proposals_cannot_overwrite_teacher_finalized_records(client, db_session, attendance_test_context):
    """
    CRITICAL RULE: AI results must NEVER overwrite teacher-finalized attendance records.
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    # Teacher manually marks student as ABSENT
    client.post(
        f"/api/v1/attendance/sessions/{session_code}/finalize",
        headers=headers_t1,
        json={"decisions": [{"student_id": "RIT2026ATT001", "status": "ABSENT", "notes": "Left class early"}]},
    )

    # Subsequent AI proposal claims student is MATCHED
    ai_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers_t1,
        json={
            "observations": [
                {
                    "track_id": "track_99",
                    "candidate_student_id": "RIT2026ATT001",
                    "match_state": "MATCHED",
                    "confidence": 0.99,
                }
            ]
        },
    )
    assert ai_res.status_code == 200
    records = ai_res.json()
    r = next(r for r in records if r["student_institutional_id"] == "RIT2026ATT001")

    # Record must remain ABSENT and is_finalized=True
    assert r["status"] == AttendanceStatus.ABSENT.value
    assert r["is_finalized"] is True
    assert r["source"] == "TEACHER_FINALIZED"


def test_manual_attendance_creates_or_updates_finalized_record(client, db_session, attendance_test_context):
    """
    Verify non-biometric manual attendance option for teachers.
    Immediately creates teacher-finalized record with source='MANUAL_ENTRY'.
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    # Teacher manually logs attendance for walk-in student
    man_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/manual",
        headers=headers_t1,
        json={"student_id": "RIT2026ATT003", "status": "PRESENT", "notes": "Manual roll call confirmation"},
    )
    assert man_res.status_code == 201
    rec = man_res.json()

    assert rec["student_institutional_id"] == "RIT2026ATT003"
    assert rec["status"] == AttendanceStatus.PRESENT.value
    assert rec["is_finalized"] is True
    assert rec["source"] == "MANUAL_ENTRY"
    assert rec["finalized_by_id"] == ctx["teacher1"].id


def test_teacher_override_requires_mandatory_audit_notes(client, db_session, attendance_test_context):
    """
    Verify attendance modifications track previous_status and require mandatory audit notes.
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    # Initial manual record as ABSENT
    man_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/manual",
        headers=headers_t1,
        json={"student_id": "RIT2026ATT002", "status": "ABSENT"},
    )
    rec_id = man_res.json()["id"]

    # Attempt to override without notes -> 400 Bad Request
    fail_res = client.put(
        f"/api/v1/attendance/records/{rec_id}",
        headers=headers_t1,
        json={"status": "PRESENT", "notes": ""},
    )
    assert fail_res.status_code == 400
    assert "Audit notes are mandatory" in fail_res.json()["detail"]

    # Override with valid audit note
    succ_res = client.put(
        f"/api/v1/attendance/records/{rec_id}",
        headers=headers_t1,
        json={"status": "PRESENT", "notes": "Student arrived late with approved medical slip"},
    )
    assert succ_res.status_code == 200
    updated = succ_res.json()

    assert updated["id"] == rec_id
    assert updated["status"] == AttendanceStatus.PRESENT.value
    assert updated["previous_status"] == AttendanceStatus.ABSENT.value
    assert updated["source"] == "TEACHER_OVERRIDE"
    assert "approved medical slip" in updated["notes"]


def test_prevent_duplicate_attendance_for_same_student_and_session(client, db_session, attendance_test_context):
    """
    Verify unique constraint on (session_id, student_id) prevents duplicate records.
    Direct repository insertion of duplicate raises 409 Conflict.
    """
    ctx = attendance_test_context
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    session_obj = session_service.create_session(
        db_session,
        session_in=SessionCreate(classroom_id=ctx["classroom"].id, subject_id=ctx["subject"].id),
        current_user=ctx["teacher1"],
    )

    s1 = ctx["students"][0]
    record_data = {
        "session_id": session_obj.id,
        "session_code": session_obj.session_id,
        "student_id": s1.id,
        "student_institutional_id": s1.student_id,
        "status": AttendanceStatus.PRESENT.value,
        "is_finalized": True,
        "source": "MANUAL_ENTRY",
    }
    # First creation succeeds
    rec1 = attendance_repository.create(db_session, record_data=record_data)
    assert rec1 is not None

    # Duplicate creation fails with 409 Conflict
    with pytest.raises(Exception) as exc_info:
        attendance_repository.create(db_session, record_data=record_data)
    assert "already exists" in str(exc_info.value) or "409" in str(exc_info.value)


def test_teacher_access_control_isolation(client, db_session, attendance_test_context):
    """
    Verify Teacher A cannot view or finalize attendance for Teacher B's session (403 Forbidden).
    Admin has full cross-teacher access.
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    headers_t2 = {"Authorization": f"Bearer {ctx['t2_token']}"}
    headers_admin = {"Authorization": f"Bearer {ctx['admin_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    # Teacher 1 starts session
    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    # Teacher 2 attempts to view session attendance -> 403 Forbidden
    t2_get = client.get(f"/api/v1/attendance/sessions/{session_code}", headers=headers_t2)
    assert t2_get.status_code == 403
    assert "Access denied" in t2_get.json()["detail"]

    # Teacher 2 attempts to finalize Teacher 1's session -> 403 Forbidden
    t2_fin = client.post(
        f"/api/v1/attendance/sessions/{session_code}/finalize",
        headers=headers_t2,
        json={"decisions": [{"student_id": "RIT2026ATT001", "status": "PRESENT"}]},
    )
    assert t2_fin.status_code == 403

    # Admin can view Teacher 1's session attendance
    admin_get = client.get(f"/api/v1/attendance/sessions/{session_code}", headers=headers_admin)
    assert admin_get.status_code == 200


def test_unauthenticated_attendance_access_rejected(client):
    """
    Verify anonymous requests without a valid bearer token are rejected with 401 Unauthorized.
    """
    res1 = client.get("/api/v1/attendance/sessions/SES-1234")
    assert res1.status_code == 401

    res2 = client.post("/api/v1/attendance/sessions/SES-1234/proposals", json={"observations": []})
    assert res2.status_code == 401

    res3 = client.post("/api/v1/attendance/sessions/SES-1234/finalize", json={"decisions": []})
    assert res3.status_code == 401

    res4 = client.put("/api/v1/attendance/records/1", json={"status": "PRESENT", "notes": "note"})
    assert res4.status_code == 401


def test_student_attendance_history_retrieval(client, db_session, attendance_test_context):
    """
    Verify student attendance history can be queried by institutional student_id string.
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    # Record attendance for RIT2026ATT001
    client.post(
        f"/api/v1/attendance/sessions/{session_code}/manual",
        headers=headers_t1,
        json={"student_id": "RIT2026ATT001", "status": "PRESENT", "notes": "Present in lab"},
    )

    # Query student history
    hist_res = client.get("/api/v1/attendance/students/RIT2026ATT001", headers=headers_t1)
    assert hist_res.status_code == 200
    records = hist_res.json()
    assert len(records) >= 1
    assert records[0]["student_institutional_id"] == "RIT2026ATT001"
    assert records[0]["status"] == AttendanceStatus.PRESENT.value


def test_cancelled_or_completed_session_rejects_ai_proposals(client, db_session, attendance_test_context):
    """
    Verify AI proposals cannot be submitted to a cancelled or completed session.
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    # Cancel session
    cancel_res = client.post(f"/api/v1/sessions/{session_code}/cancel", headers=headers_t1)
    assert cancel_res.status_code == 200

    # Submitting proposals to cancelled session -> 400 Bad Request
    prop_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers_t1,
        json={
            "observations": [
                {
                    "track_id": "track_1",
                    "candidate_student_id": "RIT2026ATT001",
                    "match_state": "MATCHED",
                    "confidence": 0.95,
                }
            ]
        },
    )
    assert prop_res.status_code == 400
    assert "Cannot submit AI observations" in prop_res.json()["detail"]


def test_get_single_attendance_record(client, db_session, attendance_test_context):
    """
    Verify individual attendance record retrieval by primary key ID.
    """
    ctx = attendance_test_context
    headers_t1 = {"Authorization": f"Bearer {ctx['t1_token']}"}
    _ensure_no_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers=headers_t1,
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    man_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/manual",
        headers=headers_t1,
        json={"student_id": "RIT2026ATT001", "status": "PRESENT", "notes": "Attended"},
    )
    assert man_res.status_code == 201
    rec_id = man_res.json()["id"]

    rec_res = client.get(f"/api/v1/attendance/records/{rec_id}", headers=headers_t1)
    assert rec_res.status_code == 200
    assert rec_res.json()["id"] == rec_id
    assert rec_res.json()["student_institutional_id"] == "RIT2026ATT001"

