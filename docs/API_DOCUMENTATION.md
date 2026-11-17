# RIT-SYNC VISION — Backend API Documentation

**Version:** `1.0.0 (API v1)`  
**Audience:** Frontend Development Team (Lead: Rakesh), Integration & QA  
**Backend Base URL (Local Development):** `http://localhost:8000/api/v1`  
**Root Health Check:** `http://localhost:8000/health`  
**OpenAPI Specification:** `http://localhost:8000/openapi.json`  
**Swagger Interactive UI:** `http://localhost:8000/docs`

---

## 1. Architectural Overview & Authentication

### 1.1 Base Configuration
The FastAPI backend runs locally at `http://localhost:8000` (or `http://0.0.0.0:8000`). All application APIs are versioned under the `/api/v1` prefix. Cross-Origin Resource Sharing (CORS) is enabled for browser clients (`allow_origins=["*"]`, `allow_credentials=True`).

### 1.2 Authentication Schemes
The backend supports two distinct authentication mechanisms:

1. **User JWT Bearer Authentication**:
   - Used for all user-facing frontend operations (Admin and Teacher).
   - Delivered via standard HTTP header:
     ```http
     Authorization: Bearer <jwt_access_token>
     ```
   - Tokens are HMAC-SHA256 (HS256) signed JSON Web Tokens carrying `sub` (username), `role` (`admin` or `teacher`), and an expiration timestamp (`exp`).

2. **Camera / Capture Permit Authentication**:
   - Used by edge camera ingest agents and AI observation pipelines.
   - Delivered via dedicated secure header:
     ```http
     X-Permit-Token: <cryptographic_permit_token>
     ```
   - Time-bound and bound strictly to an active session, classroom, and teacher. Raw tokens are never stored in the database (stored as SHA-256 hashes).

### 1.3 Role-Based Access Control (RBAC)
- **`admin`**: Full system access. Owns User, Student, Classroom, and Subject CRUD. Can view and manage all capture sessions and attendance records.
- **`teacher`**: Read-only access to Students, Classrooms, and Subjects. Exclusive ownership over their own capture sessions, active permits, attendance reviews, manual roll-calls, overrides, and offline sync. Teachers cannot access or modify sessions owned by other teachers.

---

## 2. Attendance States & Critical Business Invariants

Frontend displays and state machines must strictly adhere to the standardized attendance states defined in **MANAGE.md §5**:

| Status Key | Type | Description |
|---|---|---|
| `PRESENT_CANDIDATE` | Candidate | Sufficient system evidence from camera/AI; awaits teacher review. |
| `NEEDS_REVIEW` | Candidate | Ambiguous or marginal confidence match; requires explicit teacher decision. |
| `NOT_OBSERVED` | Informational | System obtained no observation evidence for this enrolled student. |
| `PRESENT` | Finalized | Explicit teacher-finalized present decision. |
| `ABSENT` | Finalized | Explicit teacher-authorized absence decision. |

### CRITICAL ATTENDANCE INVARIANTS:
1. **`NOT_OBSERVED` DOES NOT MEAN `ABSENT`**:
   The frontend must never display `NOT_OBSERVED` as absent, nor calculate attendance reports treating unobserved students as absent.
2. **AI Observations Never Finalize Attendance**:
   AI pipeline results create proposals only (`is_finalized = false`). Only an explicit teacher action can finalize records.
3. **Teacher Decisions are Protected**:
   AI proposals cannot overwrite, degrade, or revert a teacher-finalized record.
4. **Manual Attendance Alternative**:
   Teachers can mark attendance manually without biometric input at any time.

---

## 3. Endpoints Reference

---

### Section A: System Health & Status

#### `GET /health`
- **Description:** Root health check for reverse proxies and orchestrators.
- **Auth:** None.
- **Example Response (`200 OK`):**
  ```json
  {
    "status": "ok",
    "service": "rit-sync-vision-backend"
  }
  ```

#### `GET /api/v1/health`
- **Description:** Versioned API health check.
- **Auth:** None.
- **Example Response (`200 OK`):**
  ```json
  {
    "status": "ok",
    "service": "rit-sync-vision-backend",
    "version": "v1"
  }
  ```

---

### Section B: Authentication

#### `POST /api/v1/auth/login`
- **Description:** Authenticate using username or email and password.
- **Auth:** None.
- **Request Body (`application/json`):**
  ```json
  {
    "username": "prof.sharma",
    "password": "TeacherPassword123!"
  }
  ```
  *(Note: The `username` field also accepts an email address e.g. `"prof.sharma@rit.edu"`)*
- **Response (`200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "role": "teacher",
    "user_id": 2,
    "username": "prof.sharma"
  }
  ```
- **Errors:**
  - `401 Unauthorized`: Invalid credentials or inactive account.
  - `422 Unprocessable Entity`: Validation failure (missing fields).

#### `GET /api/v1/auth/me`
- **Description:** Retrieve currently authenticated user profile.
- **Auth:** `Bearer <token>` (Teacher or Admin).
- **Response (`200 OK`):**
  ```json
  {
    "id": 2,
    "email": "prof.sharma@rit.edu",
    "username": "prof.sharma",
    "full_name": "Dr. Ramesh Sharma",
    "role": "teacher",
    "is_active": true,
    "created_at": "2026-11-01T09:00:00Z",
    "updated_at": "2026-11-01T09:00:00Z"
  }
  ```
- **Errors:**
  - `401 Unauthorized`: Missing, expired, or invalid token.

---

### Section C: Users Management

#### `GET /api/v1/users/`
- **Description:** List registered users with pagination.
- **Auth:** `Bearer <token>` (`admin` only).
- **Query Parameters:**
  - `skip` (int, default: 0)
  - `limit` (int, default: 100)
- **Response (`200 OK`):** Array of User objects.
- **Errors:**
  - `403 Forbidden`: Authenticated user is not an Admin.

#### `POST /api/v1/users/`
- **Description:** Register a new user account.
- **Auth:** `Bearer <token>` (`admin` only).
- **Request Body:**
  ```json
  {
    "email": "faculty.patel@rit.edu",
    "username": "prof.patel",
    "full_name": "Prof. Ananya Patel",
    "password": "SecurePassword123!",
    "role": "teacher"
  }
  ```
- **Response (`201 Created`):** Created User object.
- **Errors:**
  - `409 Conflict`: Email or username already registered.

#### `GET /api/v1/users/{user_id}`
- **Description:** Retrieve single user by database ID.
- **Auth:** `Bearer <token>` (`admin` or self only).
- **Path Parameters:** `user_id` (int).
- **Errors:**
  - `403 Forbidden`: Attempting to inspect another user's profile without admin role.
  - `404 Not Found`: User does not exist.

---

### Section D: Students Management

*CRITICAL INTEGRATION NOTE:* In student lookup, update, and deletion endpoints, the URL path parameter `{student_id}` accepts the **institutional string identifier** (e.g. `"RIT2026CS001"`), **NOT** the internal database primary key integer.

#### `GET /api/v1/students/`
- **Description:** List students with pagination.
- **Auth:** `Bearer <token>` (Teacher or Admin).
- **Query Parameters:** `skip` (int, default: 0), `limit` (int, default: 100).
- **Response (`200 OK`):**
  ```json
  [
    {
      "id": 1,
      "student_id": "RIT2026CS001",
      "first_name": "Aarav",
      "last_name": "Verma",
      "email": "aarav.verma@rit.edu",
      "is_active": true,
      "is_enrolled": true,
      "created_at": "2026-11-01T10:00:00Z",
      "updated_at": "2026-11-01T10:00:00Z"
    }
  ]
  ```

#### `POST /api/v1/students/`
- **Description:** Register a new student record.
- **Auth:** `Bearer <token>` (`admin` only).
- **Request Body:**
  ```json
  {
    "student_id": "RIT2026CS042",
    "first_name": "Diya",
    "last_name": "Menon",
    "email": "diya.menon@rit.edu",
    "is_active": true,
    "is_enrolled": true
  }
  ```
- **Response (`201 Created`):** Created Student object.
- **Errors:**
  - `409 Conflict`: Institutional student ID or email already exists.

#### `GET /api/v1/students/{student_id}`
- **Description:** Retrieve student details by institutional ID string.
- **Auth:** `Bearer <token>` (Teacher or Admin).
- **Path Parameter:** `student_id` (string, e.g. `"RIT2026CS001"`).
- **Response (`200 OK`):** Single Student object.
- **Errors:**
  - `404 Not Found`: Student not found.

#### `PUT /api/v1/students/{student_id}`
- **Description:** Update student details by institutional ID string.
- **Auth:** `Bearer <token>` (`admin` only).
- **Request Body:**
  ```json
  {
    "first_name": "Diya",
    "last_name": "Nair",
    "is_enrolled": true
  }
  ```
- **Response (`200 OK`):** Updated Student object.

#### `DELETE /api/v1/students/{student_id}`
- **Description:** Delete student record by institutional ID string.
- **Auth:** `Bearer <token>` (`admin` only).
- **Response (`200 OK`):**
  ```json
  {
    "status": "ok",
    "message": "Student with identifier 'RIT2026CS042' successfully deleted"
  }
  ```

---

### Section E: Classrooms Management

#### `GET /api/v1/classrooms/`
- **Description:** List registered classrooms.
- **Auth:** `Bearer <token>` (Teacher or Admin).
- **Response (`200 OK`):**
  ```json
  [
    {
      "id": 1,
      "room_number": "LH-101",
      "name": "Lecture Hall 101",
      "capacity": 60,
      "camera_stream_url": "rtsp://camera.campus.internal/lh101",
      "is_active": true,
      "created_at": "2026-11-01T09:00:00Z",
      "updated_at": "2026-11-01T09:00:00Z"
    }
  ]
  ```

#### `POST /api/v1/classrooms/`
- **Description:** Create classroom.
- **Auth:** `Bearer <token>` (`admin` only).
- **Request Body:**
  ```json
  {
    "room_number": "LH-201",
    "name": "Lecture Hall 201",
    "capacity": 75,
    "camera_stream_url": "rtsp://camera.campus.internal/lh201",
    "is_active": true
  }
  ```
- **Response (`201 Created`):** Created Classroom object.

#### `GET /api/v1/classrooms/{classroom_id}`
- **Description:** Get single classroom by integer ID.
- **Auth:** `Bearer <token>` (Teacher or Admin).

#### `PUT /api/v1/classrooms/{classroom_id}`
- **Description:** Update classroom details by integer ID.
- **Auth:** `Bearer <token>` (`admin` only).

#### `DELETE /api/v1/classrooms/{classroom_id}`
- **Description:** Delete classroom by integer ID.
- **Auth:** `Bearer <token>` (`admin` only).

---

### Section F: Subjects Management

#### `GET /api/v1/subjects/`
- **Description:** List registered courses/subjects.
- **Auth:** `Bearer <token>` (Teacher or Admin).
- **Response (`200 OK`):**
  ```json
  [
    {
      "id": 1,
      "subject_code": "CS301",
      "name": "Computer Vision",
      "department": "Computer Science",
      "credits": 4,
      "is_active": true,
      "created_at": "2026-11-01T09:00:00Z",
      "updated_at": "2026-11-01T09:00:00Z"
    }
  ]
  ```

#### `POST /api/v1/subjects/`
- **Description:** Create subject.
- **Auth:** `Bearer <token>` (`admin` only).
- **Request Body:**
  ```json
  {
    "subject_code": "CS402",
    "name": "Distributed Systems",
    "department": "Computer Science",
    "credits": 3,
    "is_active": true
  }
  ```

#### `GET /api/v1/subjects/{subject_id}`
- **Description:** Get subject by integer ID.
- **Auth:** `Bearer <token>` (Teacher or Admin).

#### `PUT /api/v1/subjects/{subject_id}`
- **Description:** Update subject by integer ID.
- **Auth:** `Bearer <token>` (`admin` only).

#### `DELETE /api/v1/subjects/{subject_id}`
- **Description:** Delete subject by integer ID.
- **Auth:** `Bearer <token>` (`admin` only).

---

### Section G: Capture Sessions & Permits

#### `POST /api/v1/sessions/`
- **Description:** Start an authorized classroom capture session and issue a time-bound permit.
- **Auth:** `Bearer <token>` (Teacher or Admin).
- **Request Body:**
  ```json
  {
    "classroom_id": 1,
    "subject_id": 1,
    "duration_minutes": 60,
    "camera_stream_url": "rtsp://camera.campus.internal/lh101"
  }
  ```
- **Response (`201 Created`):**
  ```json
  {
    "id": 12,
    "session_id": "SES-20261117-9876",
    "classroom_id": 1,
    "subject_id": 1,
    "teacher_id": 2,
    "status": "ACTIVE",
    "camera_stream_url": "rtsp://camera.campus.internal/lh101",
    "start_time": "2026-11-17T10:00:00Z",
    "end_time": null,
    "expires_at": "2026-11-17T11:00:00Z",
    "created_at": "2026-11-17T10:00:00Z",
    "updated_at": "2026-11-17T10:00:00Z",
    "permit": {
      "permit_id": "PMT-20261117-5432",
      "session_id": "SES-20261117-9876",
      "permit_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "issued_to_id": 2,
      "classroom_id": 1,
      "camera_stream_url": "rtsp://camera.campus.internal/lh101",
      "issued_at": "2026-11-17T10:00:00Z",
      "expires_at": "2026-11-17T11:00:00Z",
      "is_revoked": false
    }
  }
  ```
- **Errors:**
  - `409 Conflict`: Classroom already has an active capture session (SEC-SES-03).
  - `404 Not Found`: Classroom or Subject ID not found.

#### `GET /api/v1/sessions/`
- **Description:** List capture sessions. Teachers view their own sessions; Admins view all sessions.
- **Auth:** `Bearer <token>`.
- **Response (`200 OK`):** Array of Session objects (Note: `permit.permit_token` is omitted for security in general listings).

#### `GET /api/v1/sessions/{session_id}`
- **Description:** Retrieve details of a single session by `session_id` code (e.g. `"SES-..."`) or integer ID.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).
- **Errors:**
  - `403 Forbidden`: Teacher does not own this session.

#### `POST /api/v1/sessions/{session_id}/complete`
- **Description:** Mark session as `COMPLETED`. Automatically revokes active permits.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).

#### `POST /api/v1/sessions/{session_id}/cancel`
- **Description:** Abort/cancel session (`CANCELLED`). Automatically revokes active permits.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).

#### `GET /api/v1/sessions/{session_id}/permit`
- **Description:** Retrieve or rotate active permit for ongoing session.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).

#### `POST /api/v1/sessions/permit/validate`
- **Description:** Cryptographically validate a permit token. Used by camera/AI runners.
- **Auth:** `Bearer <token>` (Authenticated caller).
- **Request Body:**
  ```json
  {
    "permit_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "valid": true,
    "session_id": "SES-20261117-9876",
    "classroom_id": 1,
    "camera_stream_url": "rtsp://camera.campus.internal/lh101",
    "expires_at": "2026-11-17T11:00:00Z",
    "error_message": null
  }
  ```

---

### Section H: Attendance Management & Teacher Review

#### `GET /api/v1/attendance/sessions/{session_id}`
- **Description:** Retrieve complete session attendance review roster and counts.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).
- **Response (`200 OK`):**
  ```json
  {
    "session_id": 12,
    "session_code": "SES-20261117-9876",
    "total_enrolled": 50,
    "present_candidates": 38,
    "needs_review": 4,
    "not_observed": 8,
    "finalized_present": 0,
    "finalized_absent": 0,
    "records": [
      {
        "id": 101,
        "session_id": 12,
        "session_code": "SES-20261117-9876",
        "student_id": 1,
        "student_institutional_id": "RIT2026CS001",
        "status": "PRESENT_CANDIDATE",
        "is_finalized": false,
        "confidence": 0.94,
        "source": "AI_PROPOSAL",
        "finalized_by_id": null,
        "finalized_at": null,
        "previous_status": null,
        "notes": null,
        "created_at": "2026-11-17T10:05:00Z",
        "updated_at": "2026-11-17T10:05:00Z"
      },
      {
        "id": 102,
        "session_id": 12,
        "session_code": "SES-20261117-9876",
        "student_id": 2,
        "student_institutional_id": "RIT2026CS002",
        "status": "NEEDS_REVIEW",
        "is_finalized": false,
        "confidence": 0.62,
        "source": "AI_PROPOSAL",
        "finalized_by_id": null,
        "finalized_at": null,
        "previous_status": null,
        "notes": null,
        "created_at": "2026-11-17T10:06:00Z",
        "updated_at": "2026-11-17T10:06:00Z"
      },
      {
        "id": 0,
        "session_id": 12,
        "session_code": "SES-20261117-9876",
        "student_id": 3,
        "student_institutional_id": "RIT2026CS003",
        "status": "NOT_OBSERVED",
        "is_finalized": false,
        "confidence": null,
        "source": "SYSTEM_PENDING",
        "finalized_by_id": null,
        "finalized_at": null,
        "previous_status": null,
        "notes": null,
        "created_at": "2026-11-17T10:00:00Z",
        "updated_at": "2026-11-17T10:00:00Z"
      }
    ]
  }
  ```

#### `POST /api/v1/attendance/sessions/{session_id}/finalize`
- **Description:** Teacher-authorized finalization of attendance. Status must be `PRESENT` or `ABSENT`.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).
- **Request Body:**
  ```json
  {
    "decisions": [
      {
        "student_id": "RIT2026CS001",
        "status": "PRESENT",
        "notes": "Verified by teacher"
      },
      {
        "student_id": "RIT2026CS002",
        "status": "PRESENT",
        "notes": "Student arrived late; confirmed"
      },
      {
        "student_id": "RIT2026CS003",
        "status": "ABSENT",
        "notes": "Not present in class"
      }
    ]
  }
  ```
- **Response (`200 OK`):** Array of finalized AttendanceRecord objects with `is_finalized: true`.

#### `POST /api/v1/attendance/sessions/{session_id}/manual`
- **Description:** Manual roll-call entry for a single student (non-biometric alternative).
- **Auth:** `Bearer <token>` (Teacher owner or Admin).
- **Request Body:**
  ```json
  {
    "student_id": "RIT2026CS004",
    "status": "PRESENT",
    "notes": "Manual roll call confirmation"
  }
  ```
- **Response (`201 Created`):** Created finalized AttendanceRecord object.

#### `GET /api/v1/attendance/records/{record_id}`
- **Description:** Retrieve single attendance record by database ID.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).

#### `PUT /api/v1/attendance/records/{record_id}`
- **Description:** Teacher/admin correction of an existing attendance record. Mandatory `notes` required for audit logging.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).
- **Request Body:**
  ```json
  {
    "status": "PRESENT",
    "notes": "Medical certificate submitted to HOD"
  }
  ```
- **Response (`200 OK`):** Updated AttendanceRecord object containing `previous_status` and audit history.

#### `GET /api/v1/attendance/students/{student_id}`
- **Description:** Retrieve attendance history across all sessions for a specific student.
- **Auth:** `Bearer <token>` (Teacher or Admin).
- **Path Parameter:** `student_id` (institutional string ID).
- **Response (`200 OK`):** Array of historical AttendanceRecord objects.

---

### Section I: AI Observation Ingestion

#### `POST /api/v1/attendance/sessions/{session_id}/proposals` (or `/observations`)
- **Description:** Ingest AI detection and matching results. Proposes candidates (`is_finalized=false`).
- **Auth Header:** `X-Permit-Token: <token>` OR `Authorization: Bearer <user_jwt>`.
- **Request Body:**
  ```json
  {
    "session_id": "SES-20261117-9876",
    "classroom_id": 1,
    "observations": [
      {
        "track_id": "track_001",
        "candidate_student_id": "RIT2026CS001",
        "match_state": "MATCHED",
        "confidence": 0.94,
        "reason_codes": ["MULTI_FRAME_CONSISTENT"],
        "evidence_count": 6
      },
      {
        "track_id": "track_002",
        "candidate_student_id": "RIT2026CS002",
        "match_state": "NEEDS_REVIEW",
        "confidence": 0.61,
        "reason_codes": ["LOW_CONFIDENCE"],
        "evidence_count": 2
      },
      {
        "track_id": "track_003",
        "candidate_student_id": null,
        "match_state": "UNKNOWN",
        "confidence": 0.32,
        "reason_codes": ["OPEN_SET_UNKNOWN"],
        "evidence_count": 3
      }
    ]
  }
  ```
- **Response (`200 OK`):** Array of candidate AttendanceRecord objects.
- **Errors:**
  - `401 Unauthorized`: Permit token expired, revoked, or invalid.
  - `400 Bad Request`: Session expired/completed/cancelled, or classroom/session ID mismatch.

#### `GET /api/v1/attendance/ai-status`
- **Description:** Returns AI engine integration interface and readiness status.
- **Auth:** None.

---

### Section J: Offline Synchronization

Used by mobile or web clients operating in offline/disconnected environments. Local operations queued client-side must be submitted in batches when connectivity is restored.

#### `GET /api/v1/sync/status`
- **Description:** Status and readiness check for offline sync engine.
- **Auth:** None.
- **Response (`200 OK`):**
  ```json
  {
    "status": "ready",
    "module": "synchronization",
    "version": "1.0.0"
  }
  ```

#### `POST /api/v1/sync/attendance`
- **Description:** Submit a batch of offline attendance events idempotently.
- **Auth:** `Bearer <token>` (Teacher or Admin).
- **Request Body:**
  ```json
  {
    "events": [
      {
        "event_id": "evt-7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "session_id": "SES-20261117-9876",
        "student_id": "RIT2026CS001",
        "event_type": "RECORD_ATTENDANCE",
        "status": "PRESENT",
        "notes": "Scanned offline with tablet",
        "client_timestamp": "2026-11-17T10:15:00Z"
      },
      {
        "event_id": "evt-8a1f2233-1111-40de-944b-e07fc1f90bb8",
        "session_id": "SES-20261117-9876",
        "student_id": "RIT2026CS002",
        "event_type": "RECORD_ATTENDANCE",
        "status": "ABSENT",
        "notes": "Marked absent offline",
        "client_timestamp": "2026-11-17T10:15:30Z"
      }
    ]
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "total_events": 2,
    "synced_count": 2,
    "duplicate_count": 0,
    "conflict_count": 0,
    "rejected_count": 0,
    "results": [
      {
        "event_id": "evt-7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "session_id": "SES-20261117-9876",
        "student_id": "RIT2026CS001",
        "status": "SYNCED",
        "message": "Successfully synchronized offline attendance event 'evt-7c9e6679...'",
        "attendance_record_id": 101,
        "server_timestamp": "2026-11-17T10:30:00Z"
      },
      {
        "event_id": "evt-8a1f2233-1111-40de-944b-e07fc1f90bb8",
        "session_id": "SES-20261117-9876",
        "student_id": "RIT2026CS002",
        "status": "SYNCED",
        "message": "Successfully synchronized offline attendance event 'evt-8a1f2233...'",
        "attendance_record_id": 102,
        "server_timestamp": "2026-11-17T10:30:00Z"
      }
    ]
  }
  ```
- **Sync Status Values & Behavior:**
  - `SYNCED`: Event successfully processed and attendance record created/finalized.
  - `DUPLICATE`: Client resubmitted the same `event_id` with identical data (e.g. after a network timeout). Acknowledged safely without duplicating attendance records.
  - `CONFLICT`:
    - Case 1: `event_id` was reused with differing data (idempotency key collision).
    - Case 2: Event contradicts an already teacher-finalized record. Finalized records are **never** silently overwritten.
  - `REJECTED`: Event references an invalid student, cancelled session, or caller is unauthorized.

#### `GET /api/v1/sync/events/{event_id}`
- **Description:** Inspect status and audit details of a single synchronization event.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).

#### `GET /api/v1/sync/sessions/{session_id}/events`
- **Description:** List all sync events associated with a capture session.
- **Auth:** `Bearer <token>` (Teacher owner or Admin).

---

## 4. Unimplemented / Out-of-Scope Features for Frontend

To avoid broken client calls, Rakesh should note that the following features are **not** implemented in the backend API:

1. **Reports Module (`/api/v1/reports/*`)**:
   - The directory `backend/app/modules/reports` is currently empty.
   - Aggregate PDF/Excel reporting and department-wide analytics endpoints are not yet implemented.
   - *Workaround for Frontend:* Aggregate data from `GET /api/v1/attendance/sessions/{session_id}` and `GET /api/v1/attendance/students/{student_id}`.
2. **User Modification & Deletion (`PUT /api/v1/users/{id}`, `DELETE /api/v1/users/{id}`)**:
   - Currently, user accounts can only be created (`POST`) and retrieved (`GET`). Updating and deleting user accounts via REST are not registered in the API router.
3. **Face Registration Endpoints (`/api/v1/face-registration/*`)**:
   - Biometric face template ingestion and camera calibration routes do not exist as REST APIs. Face enrolment metadata is managed internally through student attributes.
