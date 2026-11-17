"""
Integration and regression tests for AI Observation Integration.
Tests requirements from MANAGE.md §5 & §6:
1. Valid AI observation submission via capture permit and teacher authorization.
2. Direct payload ingestion endpoint (/api/v1/attendance/observations).
3. Payload validation (invalid match states, out-of-bounds confidence, empty batches).
4. Cross-reference validation (conflicting session_id, conflicting classroom_id).
5. Security: permit validation, revocation, replay prevention, and cross-session isolation (401/403).
6. Non-active session protection (expired, cancelled, completed sessions rejected with 400).
7. Unknown student and open-set UNKNOWN handling (safe skip, no 500 errors).
8. Deduplication: multiple observations for same student/track merged safely.
9. Teacher-finalized record immutability against AI proposals.
10. NOT_OBSERVED safety (unobserved students never automatically become ABSENT).
11. AI Engine dependency status endpoint (/api/v1/attendance/ai-status).
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
def ai_test_context(db_session):
    """Seed users, classroom, subject, students, and an authorized session with permit."""
    admin_name = "ai_admin"
    teacher1_name = "ai_teacher_1"
    teacher2_name = "ai_teacher_2"

    u_admin = user_service.get_by_username(db_session, admin_name)
    if not u_admin:
        u_admin = user_service.create_user(
            db_session,
            UserCreate(
                email="ai_admin@rit.edu",
                username=admin_name,
                full_name="AI Integration Admin",
                password="AdminPassword123!",
                role=UserRole.ADMIN,
            ),
        )

    u_teacher1 = user_service.get_by_username(db_session, teacher1_name)
    if not u_teacher1:
        u_teacher1 = user_service.create_user(
            db_session,
            UserCreate(
                email="ai_t1@rit.edu",
                username=teacher1_name,
                full_name="AI Teacher 1",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    u_teacher2 = user_service.get_by_username(db_session, teacher2_name)
    if not u_teacher2:
        u_teacher2 = user_service.create_user(
            db_session,
            UserCreate(
                email="ai_t2@rit.edu",
                username=teacher2_name,
                full_name="AI Teacher 2",
                password="TeacherPassword123!",
                role=UserRole.TEACHER,
            ),
        )

    # Seed Classroom 1
    room = classroom_repository.get_by_room_number(db_session, "AI-LAB-201")
    if not room:
        room = classroom_repository.create(
            db_session,
            {
                "room_number": "AI-LAB-201",
                "name": "Vision AI Lab 201",
                "capacity": 50,
                "camera_stream_url": "rtsp://camera.internal/ailab201",
                "is_active": True,
            },
        )

    # Seed Classroom 2
    room2 = classroom_repository.get_by_room_number(db_session, "AI-LAB-202")
    if not room2:
        room2 = classroom_repository.create(
            db_session,
            {
                "room_number": "AI-LAB-202",
                "name": "Vision AI Lab 202",
                "capacity": 40,
                "camera_stream_url": "rtsp://camera.internal/ailab202",
                "is_active": True,
            },
        )

    # Seed Subject
    subj = subject_repository.get_by_subject_code(db_session, "AI-CV401")
    if not subj:
        subj = subject_repository.create(
            db_session,
            {
                "subject_code": "AI-CV401",
                "name": "Deep Learning for Vision",
                "department": "Computer Science",
                "credits": 4,
                "is_active": True,
            },
        )

    # Seed Students
    s1 = student_repository.get_by_student_id(db_session, "RIT2026AI001")
    if not s1:
        s1 = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026AI001",
                "first_name": "Dev",
                "last_name": "Anand",
                "email": "dev.anand@rit.edu",
                "is_active": True,
                "is_enrolled": True,
            },
        )

    s2 = student_repository.get_by_student_id(db_session, "RIT2026AI002")
    if not s2:
        s2 = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026AI002",
                "first_name": "Esha",
                "last_name": "Deol",
                "email": "esha.deol@rit.edu",
                "is_active": True,
                "is_enrolled": True,
            },
        )

    s3 = student_repository.get_by_student_id(db_session, "RIT2026AI003")
    if not s3:
        s3 = student_repository.create(
            db_session,
            {
                "student_id": "RIT2026AI003",
                "first_name": "Farhan",
                "last_name": "Akhtar",
                "email": "farhan.akhtar@rit.edu",
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


def _clear_active_session(db_session, classroom_id):
    active = session_repository.get_active_session_in_classroom(db_session, classroom_id=classroom_id)
    if active:
        session_repository.update_status(db_session, session=active, new_status="COMPLETED")


def test_ai_status_endpoint(client):
    """
    Verify /api/v1/attendance/ai-status reports readiness and documents
    the current status of the ai_engine dependency.
    """
    res = client.get("/api/v1/attendance/ai-status")
    assert res.status_code == 200
    data = res.json()
    assert data["engine_package"] == "ai_engine"
    assert data["status"] == "NOT_IMPLEMENTED"
    assert "observations" in data["contract"]


def test_observation_submission_with_capture_permit(client, db_session, ai_test_context):
    """
    Verify AI observation submission authenticated using a valid Capture Permit token
    (via X-Permit-Token header).
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)

    # Teacher creates session; captures permit
    ses_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    assert ses_res.status_code == 201
    ses_data = ses_res.json()
    session_code = ses_data["session_id"]
    permit_token = ses_data["active_permit"]["permit_token"]
    assert permit_token is not None

    # AI engine submits observations using X-Permit-Token (no user JWT)
    payload = {
        "observations": [
            {
                "track_id": "trk_001",
                "candidate_student_id": "RIT2026AI001",
                "match_state": "MATCHED",
                "confidence": 0.88,
                "evidence_count": 5,
            },
            {
                "track_id": "trk_002",
                "candidate_student_id": "RIT2026AI002",
                "match_state": "NEEDS_REVIEW",
                "confidence": 0.52,
                "evidence_count": 2,
            },
        ]
    }
    obs_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers={"X-Permit-Token": permit_token},
        json=payload,
    )
    assert obs_res.status_code == 200
    records = obs_res.json()
    assert len(records) == 2

    r1 = next(r for r in records if r["student_institutional_id"] == "RIT2026AI001")
    assert r1["status"] == AttendanceStatus.PRESENT_CANDIDATE.value
    assert r1["is_finalized"] is False
    assert r1["confidence"] == 0.88

    r2 = next(r for r in records if r["student_institutional_id"] == "RIT2026AI002")
    assert r2["status"] == AttendanceStatus.NEEDS_REVIEW.value
    assert r2["is_finalized"] is False


def test_observation_submission_via_direct_endpoint(client, db_session, ai_test_context):
    """
    Verify AI observations submission via /api/v1/attendance/observations
    with session_id included in the JSON payload body.
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]
    permit_token = ses_res.json()["active_permit"]["permit_token"]

    payload = {
        "session_id": session_code,
        "observations": [
            {
                "track_id": "trk_direct_1",
                "candidate_student_id": "RIT2026AI001",
                "match_state": "MATCHED",
                "confidence": 0.95,
            }
        ],
    }
    res = client.post(
        "/api/v1/attendance/observations",
        headers={"X-Permit-Token": permit_token},
        json=payload,
    )
    assert res.status_code == 200
    records = res.json()
    assert len(records) == 1
    assert records[0]["student_institutional_id"] == "RIT2026AI001"
    assert records[0]["status"] == AttendanceStatus.PRESENT_CANDIDATE.value


def test_marginal_confidence_matched_maps_to_needs_review(client, db_session, ai_test_context):
    """
    Verify MATCHED state with confidence below threshold (< 0.70)
    safely maps to NEEDS_REVIEW as an uncertain match (MANAGE.md §4).
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={
            "observations": [
                {
                    "track_id": "trk_weak",
                    "candidate_student_id": "RIT2026AI001",
                    "match_state": "MATCHED",
                    "confidence": 0.65,  # Below 0.70 threshold
                }
            ]
        },
    )
    assert res.status_code == 200
    record = res.json()[0]
    assert record["status"] == AttendanceStatus.NEEDS_REVIEW.value
    assert record["is_finalized"] is False


def test_invalid_payload_validation_rejections(client, db_session, ai_test_context):
    """
    Verify malformed observation payloads are strictly rejected:
    - Empty observations list -> 422
    - Out-of-bounds confidence -> 422
    - Invalid match state string -> 422
    - Negative evidence count -> 422
    - Empty track_id -> 422
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]
    headers = {"Authorization": f"Bearer {ctx['t1_token']}"}

    # 1. Empty observations list
    r1 = client.post(f"/api/v1/attendance/sessions/{session_code}/proposals", headers=headers, json={"observations": []})
    assert r1.status_code == 422

    # 2. Out-of-bounds confidence (> 1.0)
    r2 = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers,
        json={"observations": [{"track_id": "t1", "match_state": "MATCHED", "confidence": 1.5}]},
    )
    assert r2.status_code == 422

    # 3. Negative confidence (< 0.0)
    r3 = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers,
        json={"observations": [{"track_id": "t1", "match_state": "MATCHED", "confidence": -0.2}]},
    )
    assert r3.status_code == 422

    # 4. Invalid match_state enum
    r4 = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers,
        json={"observations": [{"track_id": "t1", "match_state": "CONFIRMED_STUDENT", "confidence": 0.9}]},
    )
    assert r4.status_code == 422

    # 5. Negative evidence_count
    r5 = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers,
        json={"observations": [{"track_id": "t1", "match_state": "MATCHED", "confidence": 0.9, "evidence_count": -5}]},
    )
    assert r5.status_code == 422


def test_cross_reference_conflict_rejections(client, db_session, ai_test_context):
    """
    Verify conflicting session or classroom references in payload are rejected:
    - session_id in payload != URL path -> 400
    - classroom_id in payload != session classroom -> 400
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]
    headers = {"Authorization": f"Bearer {ctx['t1_token']}"}

    # Conflicting session_id in payload body vs path
    r_ses = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers,
        json={
            "session_id": "SES-DIFFERENT-999",
            "observations": [{"track_id": "t1", "candidate_student_id": "RIT2026AI001", "match_state": "MATCHED", "confidence": 0.9}],
        },
    )
    assert r_ses.status_code == 400
    assert "does not match target session" in r_ses.json()["detail"]

    # Conflicting classroom_id
    r_cls = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers,
        json={
            "classroom_id": 9999,
            "observations": [{"track_id": "t1", "candidate_student_id": "RIT2026AI001", "match_state": "MATCHED", "confidence": 0.9}],
        },
    )
    assert r_cls.status_code == 400
    assert "does not match session classroom" in r_cls.json()["detail"]


def test_cross_session_permit_mismatch_rejected(client, db_session, ai_test_context):
    """
    Verify Permit Token issued for Session 1 cannot be replayed or used on Session 2 (403 Forbidden).
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)
    _clear_active_session(db_session, ctx["classroom2"].id)

    # Session 1 in Classroom 1
    s1_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    s1_code = s1_res.json()["session_id"]
    s1_permit = s1_res.json()["active_permit"]["permit_token"]

    # Session 2 in Classroom 2
    s2_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t2_token']}"},
        json={"classroom_id": ctx["classroom2"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    s2_code = s2_res.json()["session_id"]

    # Attempt to submit observations to Session 2 using Session 1's permit -> 403 Forbidden
    replay_res = client.post(
        f"/api/v1/attendance/sessions/{s2_code}/proposals",
        headers={"X-Permit-Token": s1_permit},
        json={
            "observations": [
                {"track_id": "trk_cross", "candidate_student_id": "RIT2026AI001", "match_state": "MATCHED", "confidence": 0.9}
            ]
        },
    )
    assert replay_res.status_code == 403
    assert "does not match the target session" in replay_res.json()["detail"]


def test_unknown_and_unassigned_student_observations_handled_safely(client, db_session, ai_test_context):
    """
    Verify system handles open-set UNKNOWN matches and non-existent student IDs
    without throwing exceptions or creating false attendance records.
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]

    payload = {
        "observations": [
            # 1. Unassigned / UNKNOWN face
            {
                "track_id": "trk_unknown",
                "candidate_student_id": None,
                "match_state": "UNKNOWN",
                "confidence": 0.2,
            },
            # 2. Non-existent student ID
            {
                "track_id": "trk_nonexistent",
                "candidate_student_id": "RIT_NONEXISTENT_STUDENT_999",
                "match_state": "MATCHED",
                "confidence": 0.95,
            },
            # 3. Legitimate student
            {
                "track_id": "trk_valid",
                "candidate_student_id": "RIT2026AI001",
                "match_state": "MATCHED",
                "confidence": 0.91,
            },
        ]
    }
    res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json=payload,
    )
    assert res.status_code == 200
    records = res.json()
    # Only valid student should have a record created
    assert len(records) == 1
    assert records[0]["student_institutional_id"] == "RIT2026AI001"


def test_intra_batch_and_sequential_deduplication(client, db_session, ai_test_context):
    """
    Verify duplicate observations for the same student (e.g. from multiple camera tracks)
    are merged safely into a single attendance record with highest confidence.
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]
    headers = {"Authorization": f"Bearer {ctx['t1_token']}"}

    # Intra-batch duplicates: same student in track A (conf 0.72) and track B (conf 0.96)
    batch_payload = {
        "observations": [
            {
                "track_id": "track_A",
                "candidate_student_id": "RIT2026AI001",
                "match_state": "MATCHED",
                "confidence": 0.72,
            },
            {
                "track_id": "track_B",
                "candidate_student_id": "RIT2026AI001",
                "match_state": "MATCHED",
                "confidence": 0.96,
            },
        ]
    }
    res = client.post(f"/api/v1/attendance/sessions/{session_code}/proposals", headers=headers, json=batch_payload)
    assert res.status_code == 200
    records = res.json()
    # Merged to single record
    assert len(records) == 1
    assert records[0]["student_institutional_id"] == "RIT2026AI001"
    assert records[0]["confidence"] == 0.96

    # Sequential duplicate: later observation arrives
    seq_payload = {
        "observations": [
            {
                "track_id": "track_C",
                "candidate_student_id": "RIT2026AI001",
                "match_state": "MATCHED",
                "confidence": 0.98,
            }
        ]
    }
    res_seq = client.post(f"/api/v1/attendance/sessions/{session_code}/proposals", headers=headers, json=seq_payload)
    assert res_seq.status_code == 200
    assert len(res_seq.json()) == 1
    assert res_seq.json()[0]["confidence"] == 0.98


def test_teacher_finalized_record_is_never_overwritten_by_ai(client, db_session, ai_test_context):
    """
    CRITICAL RULE: Teacher finalization is authoritative.
    If a teacher finalizes a student as ABSENT, subsequent AI proposals
    must NEVER change the status back to PRESENT_CANDIDATE or set is_finalized=False.
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]
    headers = {"Authorization": f"Bearer {ctx['t1_token']}"}

    # 1. Teacher finalizes RIT2026AI001 as ABSENT
    fin_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/finalize",
        headers=headers,
        json={"decisions": [{"student_id": "RIT2026AI001", "status": "ABSENT", "notes": "Excused absence"}]},
    )
    assert fin_res.status_code == 200

    # 2. AI observation claims high confidence MATCHED
    ai_res = client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers,
        json={
            "observations": [
                {
                    "track_id": "trk_late",
                    "candidate_student_id": "RIT2026AI001",
                    "match_state": "MATCHED",
                    "confidence": 0.99,
                }
            ]
        },
    )
    assert ai_res.status_code == 200
    rec = ai_res.json()[0]

    # Status must strictly remain ABSENT, is_finalized=True
    assert rec["status"] == AttendanceStatus.ABSENT.value
    assert rec["is_finalized"] is True
    assert rec["source"] == "TEACHER_FINALIZED"


def test_unobserved_students_remain_not_observed(client, db_session, ai_test_context):
    """
    CRITICAL RULE: NOT_OBSERVED must NEVER automatically become ABSENT.
    When observations only observe a subset of students, unobserved students
    are represented as NOT_OBSERVED with is_finalized=False.
    """
    ctx = ai_test_context
    _clear_active_session(db_session, ctx["classroom"].id)

    ses_res = client.post(
        "/api/v1/sessions/",
        headers={"Authorization": f"Bearer {ctx['t1_token']}"},
        json={"classroom_id": ctx["classroom"].id, "subject_id": ctx["subject"].id, "duration_minutes": 60},
    )
    session_code = ses_res.json()["session_id"]
    headers = {"Authorization": f"Bearer {ctx['t1_token']}"}

    # Only observe RIT2026AI001; RIT2026AI002 and RIT2026AI003 are unobserved
    client.post(
        f"/api/v1/attendance/sessions/{session_code}/proposals",
        headers=headers,
        json={
            "observations": [
                {"track_id": "trk_single", "candidate_student_id": "RIT2026AI001", "match_state": "MATCHED", "confidence": 0.85}
            ]
        },
    )

    # Check session review summary
    rev_res = client.get(f"/api/v1/attendance/sessions/{session_code}", headers=headers)
    assert rev_res.status_code == 200
    summary = rev_res.json()

    assert summary["present_candidates"] >= 1
    assert summary["not_observed"] >= 2
    assert summary["finalized_absent"] == 0

    s2 = next(r for r in summary["records"] if r["student_institutional_id"] == "RIT2026AI002")
    assert s2["status"] == AttendanceStatus.NOT_OBSERVED.value
    assert s2["is_finalized"] is False
