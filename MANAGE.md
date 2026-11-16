# MANAGE.md --- RIT-Sync Vision

> **Purpose:** Operating rules for human developers and AI coding agents
> working on Phase 1 (Software). **Project model:** One Git repository,
> one React frontend, one FastAPI modular monolith, and an internal
> Python AI engine. **Primary rule:** Work only within your assigned
> ownership area. Do not modify another member's files or interfaces
> without coordination.

------------------------------------------------------------------------

## 1. Project Goal

RIT-Sync Vision is a classroom attendance assistant. It processes
authorized classroom camera input, detects and tracks faces, compares
them with enrolled templates, proposes attendance candidates, and lets a
teacher review and finalize records.

**Core principle: `NOT OBSERVED` does not mean `ABSENT`.**

The AI assists the teacher; it is not the final attendance authority.

### Phase 1 scope

-   Build and test the complete software using a laptop webcam and/or
    authorized sample videos.
-   Implement teacher-facing web pages, backend modules, AI processing,
    attendance review, local storage, and synchronization foundations.
-   Keep camera input and AI processing replaceable so Phase 2 hardware
    can connect without rebuilding the application.

### Not in Phase 1 unless explicitly approved

-   Dedicated Edge AI hardware integration.
-   Production deployment to the whole institution.
-   Automatic final attendance decisions.
-   Claims of perfect recognition or spoof-proof operation.
-   Separate microservices or distributed infrastructure.

------------------------------------------------------------------------

## 2. Architecture Rules

Use a **modular monolith in a monorepo**:

``` text
rit-sync-vision/
├── frontend/       # Rakesh: React + TypeScript UI
├── backend/        # Vijayalakshmi: FastAPI application and data layer
├── ai_engine/      # Paul: internal Python AI modules
├── shared/         # agreed cross-module contracts only
├── storage/        # local runtime data; never commit real data
├── docs/           # architecture, API, database, testing and setup docs
├── scripts/        # development and setup scripts
├── tests/          # cross-module integration tests
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt
├── README.md
└── MANAGE.md
```

### Runtime relationship

``` text
React frontend
    |
    | HTTP / JSON
    v
FastAPI modular monolith
    ├── Authentication and user modules
    ├── Student, class and subject modules
    ├── Session and attendance modules
    ├── Reports, audit and synchronization modules
    ├── Database layer
    └── Internal import of ai_engine Python package
             |
             └── Detection → Quality → Tracking → Recognition
                              → Attendance candidate
```

-   The frontend communicates with the backend through documented APIs.
    It must not access the database directly.
-   The backend owns application rules, persistence, authentication,
    authorization, and final attendance records.
-   `ai_engine/` is imported by the backend as a Python package in
    Phase 1. Do not create a separate AI server unless the team
    explicitly approves it.
-   AI code must not write attendance records directly to the database.
-   Keep modules independent through clear interfaces. Avoid circular
    imports.
-   Use one database access layer and one authoritative set of database
    models, owned by `backend/`.

------------------------------------------------------------------------

## 3. Ownership and File Boundaries

  -----------------------------------------------------------------------
  Owner                   Primary responsibility  Default write boundary
  ----------------------- ----------------------- -----------------------
  **Rakesh Anand**        Frontend lead           `frontend/**`

  **Pon Vijayalakshmi**   Backend, database,      `backend/**`
                          offline sync            

  **Paul Bryton Raj**     AI engine, system       `ai_engine/**`
                          architecture,           
                          integration             
  -----------------------------------------------------------------------

### Shared paths

The following are shared and require coordination before editing:

-   `shared/**`
-   `docs/**`
-   `tests/**`
-   Root configuration files (`pyproject.toml`, `requirements.txt`,
    `package.json` if added at root, `docker-compose.yml`, `.gitignore`,
    `.env.example`, `README.md`).

**Do not assume that being the system lead grants permission to rewrite
another owner's implementation.** The owner of a directory approves
changes to that directory.

### Rules for AI agents

1.  Identify the task owner before editing.
2.  Read this file and the relevant module documentation first.
3.  Run `git status` before changing files. Preserve all existing user
    changes.
4.  Edit only the assigned directory unless the task explicitly requires
    a shared change.
5.  If another directory must change, explain the dependency and
    request/record approval before editing it.
6.  Do not rename, move, delete, reformat, or replace another owner's
    files as part of unrelated work.
7.  Do not overwrite working code with a fresh scaffold.
8.  Do not invent APIs, database columns, environment variables, model
    files, or completed features. Inspect the code first.
9.  If a required contract is missing, propose the smallest contract
    change in `docs/` or `shared/` and coordinate it.
10. Keep changes focused. Avoid unrelated cleanup and large dependency
    upgrades.
11. Never commit secrets, real student data, face images, face
    templates, or raw classroom footage.
12. Report changed files, tests run, known limitations, and any
    cross-owner dependency at task completion.

If ownership is unclear, stop before editing the disputed files and ask
the team.

------------------------------------------------------------------------

## 4. Detailed Responsibilities

### Rakesh --- Frontend

Owns all user interface and browser-side behaviour:

-   Login and logout screens.
-   Teacher dashboard.
-   Classes and subjects.
-   Student list and student details.
-   Face registration interface.
-   Camera and attendance session controls.
-   Live capture status and AI processing indicators.
-   Attendance review and teacher finalization interface.
-   Attendance history and reports.
-   System status, settings, and account pages.
-   API client, frontend state, validation, loading and error states.
-   Responsive layout and accessibility basics.

Frontend rules:

-   Use React, TypeScript, and Tailwind CSS.
-   Keep reusable UI in `components/`; route-level pages in `pages/`.
-   Put HTTP calls in `services/`, not directly throughout components.
-   Define API types from agreed contracts; do not guess response
    fields.
-   Never implement recognition or attendance authority in the browser.
-   Do not store face templates or raw frames in browser storage.
-   Show `Present candidate`, `Needs review`, and `Not observed`
    distinctly.
-   A teacher action is required to finalize attendance.
-   Include empty, loading, error, offline, and permission-denied
    states.

### Vijayalakshmi --- Backend and Data

Owns FastAPI, application modules, persistence, and synchronization:

-   Authentication, roles, and permissions.
-   Users, students, classes, and subjects.
-   Student enrollment metadata and face-template persistence interface.
-   Capture session and permit management.
-   API validation and response schemas.
-   Attendance candidates and finalized attendance records.
-   Teacher corrections and audit history.
-   Local SQLite operation and database migrations.
-   Offline event queue and safe synchronization design.
-   Reports and system health endpoints.
-   Backend tests and API documentation.

Backend rules:

-   Use FastAPI with typed request/response schemas.
-   Keep route handlers thin; place business logic in services.
-   Keep database operations in repositories or the established
    data-access layer.
-   Database models and migrations are authoritative only in `backend/`.
-   Enforce authorization on the server, not only in the UI.
-   Validate all input and use transactions for related writes.
-   Make sync operations idempotent; repeated delivery must not create
    duplicate attendance.
-   Do not accept a client-supplied AI confidence value as proof of
    identity.
-   Do not finalize attendance automatically from an AI result.
-   Do not persist raw classroom frames.

### Paul --- AI and System Integration

Owns AI processing and its contract with the backend:

-   Camera input adapter for webcam and authorized video files.
-   Face detection and face-quality checks.
-   Face alignment/encoding using the selected model.
-   Open-set matching that can return `UNKNOWN`.
-   Multi-frame face tracking and evidence aggregation.
-   Duplicate-track and duplicate-candidate handling.
-   Confidence/threshold and best-vs-second-best margin evaluation.
-   Structured AI result output.
-   AI performance and recognition evaluation.
-   Privacy-safe frame lifecycle.
-   AI module tests and integration support.

AI rules:

-   Keep AI implementation inside `ai_engine/`.
-   Expose a stable Python interface for backend use; do not access
    backend database internals.
-   Return structured evidence and reason codes, not a final attendance
    status.
-   Support `UNKNOWN` and insufficient-quality outcomes.
-   Never force a match when evidence is weak.
-   Do not treat one frame as conclusive when multi-frame evidence is
    required.
-   Process raw frames in memory and discard them after processing; do
    not write frames to disk by default.
-   Keep model weights out of Git unless the team explicitly approves a
    permitted, appropriately licensed small model. Document model
    source, version, licence, and setup.
-   Do not claim liveness or anti-spoofing protection unless it is
    implemented and tested.

------------------------------------------------------------------------

## 5. Cross-Module Contracts

These interfaces must be agreed before implementation is integrated. Do
not silently change them.

### AI engine input

The backend provides a capture/session context and frames or a frame
iterator to the AI pipeline. The exact Python signature must be
documented in `docs/AI_WORKFLOW.md`.

### AI engine output

Return a structured result containing, at minimum:

``` json
{
  "session_id": "string",
  "observations": [
    {
      "track_id": "string",
      "candidate_student_id": "string or null",
      "match_state": "MATCHED | UNKNOWN | INSUFFICIENT_QUALITY | NEEDS_REVIEW",
      "confidence": 0.0,
      "reason_codes": [],
      "evidence_count": 0
    }
  ]
}
```

This is an illustrative contract. Confirm field names and types in
`shared/` before treating it as final. Do not put names, raw images, or
biometric templates in ordinary logs.

### Attendance states

Use these meanings consistently:

-   `PRESENT_CANDIDATE`: sufficient system evidence that the student was
    observed; awaits teacher finalization.
-   `NEEDS_REVIEW`: identity or evidence is uncertain and requires
    teacher action.
-   `NOT_OBSERVED`: the system did not obtain sufficient evidence of
    observation.
-   `PRESENT`: teacher-finalized present record.
-   `ABSENT`: only a teacher-authorized final decision; never infer from
    `NOT_OBSERVED` alone.

The UI, backend, database, reports, and tests must use the same
meanings.

### API contract

-   Frontend ↔ backend: HTTP JSON API, versioned under `/api/v1/`.
-   Backend ↔ AI: internal Python function/package interface in Phase 1.
-   Backend ↔ database: backend-owned repositories/models.
-   Shared request/response types and event formats belong in `shared/`
    or documented API schemas.
-   Document endpoint method, path, auth requirement, request, response,
    and error cases in `docs/API_DOCUMENTATION.md`.

------------------------------------------------------------------------

## 6. Data, Privacy, and Security

Treat face data and attendance data as sensitive.

-   Use only authorized, consented test subjects and approved sample
    data.
-   Provide a non-biometric/manual attendance alternative.
-   Do not store raw classroom frames or video by default.
-   Face templates must be protected at rest and access-controlled.
-   Keep secrets in local environment variables; commit only
    `.env.example`.
-   Restrict teacher/admin functions through server-side authorization.
-   Record teacher corrections and finalization in audit logs.
-   Use session expiry and capture authorization/permit checks.
-   Avoid putting personal data, images, templates, tokens, or secrets
    in logs.
-   Do not use real student data in automated tests or screenshots.
-   Obtain institutional approval and appropriate privacy/legal review
    before any real student pilot.

A signed event or capture permit does not, by itself, prove that an
image is genuine or that a person is live. Test replay and spoofing
risks separately; state limitations honestly.

------------------------------------------------------------------------

## 7. Offline and Synchronization Rules

-   Local attendance events must be persisted before being marked as
    safely queued.
-   Each event must have a stable unique identifier.
-   Sync must be idempotent and safe to retry.
-   Server acknowledgement must be recorded before a queued event is
    considered synchronized.
-   Conflicts must be surfaced for resolution; never silently overwrite
    a teacher-finalized record.
-   Show pending, syncing, synced, and failed states.
-   Do not duplicate records when the same event is delivered more than
    once.
-   Keep raw frames out of the synchronization queue.

------------------------------------------------------------------------

## 8. Development Workflow

### Branches

Use:

``` text
main
feature/frontend-<name>
feature/backend-<name>
feature/ai-<name>
fix/<short-description>
```

-   Do not work directly on `main`.
-   Keep branches focused and reasonably small.
-   Pull/rebase from the latest agreed base before integration.
-   Use Pull Requests for shared integration.
-   Do not force-push shared branches without agreement.

### Before coding

1.  Read `MANAGE.md`, `README.md`, and the relevant module docs.
2.  Inspect existing implementation and `git status`.
3.  Confirm ownership and acceptance criteria.
4.  Check existing contracts before adding new ones.
5.  List the files expected to change.

### While coding

1.  Follow the existing code style and patterns.
2.  Prefer small, testable changes.
3.  Add or update tests with behaviour changes.
4.  Update documentation when contracts or setup change.
5.  Do not add dependencies without explaining why.
6.  Do not create duplicate implementations of existing features.

### Before handing off

1.  Run relevant tests and linters.
2.  Check `git diff` for unrelated edits, secrets, and accidental data.
3.  Confirm no files outside the ownership boundary were changed without
    approval.
4.  Update relevant docs.
5.  Report completion using the handoff format below.

------------------------------------------------------------------------

## 9. Testing Requirements

Minimum validation before integration:

### Frontend

-   Pages render and navigation works.
-   API loading, empty, success, error, and offline states work.
-   Teacher review actions are explicit.
-   `Not observed` is never displayed as automatically absent.
-   Forms validate input and handle API errors.

### Backend

-   Authentication and role checks.
-   Request validation and error responses.
-   Student/class/session CRUD.
-   Attendance candidate and finalization rules.
-   Audit log for teacher changes.
-   Offline queue retry and idempotency.
-   Database migration and transaction tests.

### AI

-   Multiple faces in one frame.
-   Different distances, angles, lighting, and blur.
-   Unknown/unregistered people.
-   Low-quality and ambiguous faces.
-   Multi-frame tracking and temporary disappearance.
-   Duplicate candidate prevention.
-   No forced identity when evidence is insufficient.
-   Raw frames are not persisted.

### End-to-end

-   Teacher logs in.
-   Selects a class and starts an authorized session.
-   Camera input is processed.
-   AI returns candidates and reason codes.
-   Teacher reviews and finalizes records.
-   Records are saved.
-   Offline events sync without loss or duplication.

Report measured results. Do not present target values as achieved
results.

------------------------------------------------------------------------

## 10. Definition of Done

A task is complete only when:

-   It meets its stated acceptance criteria.
-   It stays within the owner's boundary or has approved cross-owner
    changes.
-   It follows existing architecture and contracts.
-   Relevant tests pass, or failures are clearly reported.
-   No secrets or real biometric data are committed.
-   Documentation is updated where needed.
-   The change is reviewable and does not include unrelated refactoring.

A feature is not complete merely because its UI exists or its endpoint
returns a hard-coded success response.

------------------------------------------------------------------------

## 11. AI Agent Task Handoff Format

Every agent must finish with:

``` text
TASK:
[What was requested]

OWNER:
[Name / responsibility]

FILES CHANGED:
- path/to/file
- path/to/file

IMPLEMENTATION:
[Brief description]

CONTRACT CHANGES:
[None / list exact changes and who approved them]

TESTS:
[Commands run and pass/fail results]

NOT DONE / LIMITATIONS:
[Remaining work or known issues]

DEPENDENCIES:
[Other owner or module needed]

GIT:
[Branch name; commit hash if committed]
```

If blocked by another module, do not create a fake substitute that
changes the agreed contract. Provide a mock only when clearly labelled
as development-only and keep it separate from production code.

------------------------------------------------------------------------

## 12. Project-Wide Agent Instruction

Before making any change, read `MANAGE.md` and identify your ownership
boundary. Preserve other members' work, follow the established
contracts, and make the smallest complete change that satisfies the
task. Do not silently change shared architecture, APIs, database models,
or another owner's files. If a cross-module change is necessary,
document the dependency and coordinate it first.

**Project priority:** Correct attendance workflow → reliable integration
→ privacy and security → tested functionality → UI polish.

**Non-negotiable principle:** AI proposes; the teacher finalizes.
`NOT OBSERVED` is never automatically `ABSENT`.
