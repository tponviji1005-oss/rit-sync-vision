# RIT-Sync Vision
## Product Requirements Document (PRD)

**Project title:** Classroom Edge AI Attendance System — RIT-Sync Vision  
**Document version:** 1.1 — Expanded Product Requirements  
**Status:** Working PRD for Phase 1 software implementation and Phase 2 hardware planning  
**Source baseline:** *RIT-Sync Vision — Revised Design, PRD v1.1, First Review Presentation* (13 slides)  
**Department / Class:** CSE / F  
**Project guide:** Dr. N. Indumathi  

### Team

| Member | Project responsibility |
|---|---|
| Paul Bryton Raj | AI engineering, system architecture and integration |
| Pon Vijayalakshmi | Backend, database and synchronization |
| Rakesh Anand | Frontend and user experience |

> Team identifiers above follow the attached presentation. Verify the register numbers against the institution's official records before submitting external documents.

---

# 1. Executive Summary

RIT-Sync Vision is a classroom attendance assistant that uses a fixed classroom camera and Edge AI to observe students during a short, authorized capture window. It detects faces, evaluates whether observations are usable, tracks faces across multiple frames, compares them against enrolled student templates using open-set 1:N recognition, and creates attendance candidates for a teacher to review.

The product is not intended to act as an automatic biometric authority. The system provides evidence and suggestions; the teacher reviews and finalizes every attendance record. A student who was not observed by the camera must not automatically be marked absent.

The system is designed around six core principles:

1. **Bounded and authorized capture:** Capture occurs only during a short, visible, authorized session.
2. **Confidence-aware recognition:** The system can return `UNKNOWN` or request review instead of forcing an identity.
3. **Evidence across frames:** Face tracklets collect observations across multiple frames rather than relying on one image.
4. **Teacher finalization:** Teachers review candidates, resolve uncertain cases and finalize records.
5. **Offline resilience:** Authorized offline sessions can create provisional local records that synchronize later.
6. **Privacy by default:** Raw frames are processed locally in memory and discarded; they are not permanently stored.

The project will be implemented in two phases:

- **Phase 1 — Software:** Build and validate the application using a laptop webcam and/or authorized sample video. Implement the user interface, backend, AI pipeline, attendance workflow, local storage and synchronization foundation.
- **Phase 2 — Hardware:** Integrate a measured classroom camera, Edge AI compute device, secure key storage, encrypted local storage, network/power fault handling and visible capture indicator.

The software architecture must allow the Phase 1 camera source to be replaced by the Phase 2 hardware camera without redesigning the attendance application.

---

# 2. Problem Statement

Traditional classroom roll-call consumes teaching time and requires manual effort. Camera-assisted attendance introduces additional risks that must be handled explicitly:

- Faces in distant rows may be too small or unclear to identify.
- Poor lighting, blur, face angle and occlusion can reduce recognition quality.
- A wrong identity match may hide an absent student or incorrectly mark another student present.
- A student who is not detected may be incorrectly treated as absent.
- A camera may not cover every seat equally.
- Photo or video replay may attempt to fool the recognition system.
- Network outages may interrupt synchronization.
- Biometric data creates privacy, consent and security responsibilities.

The key design correction is:

> **Not observed ≠ Absent.**

A missing or poor-quality observation is an evidence gap. It is not proof that the student is absent.

---

# 3. Product Vision

Deliver a confidence-aware classroom attendance assistant that reduces the time and effort required for attendance while preserving teacher control, clear uncertainty handling, privacy-conscious processing and resilience to network outages.

## 3.1 Product statement

For teachers and educational institutions that need a more efficient way to manage classroom attendance, RIT-Sync Vision provides a local AI-assisted observation and review workflow. It proposes which enrolled students were observed during an authorized window, explains uncertain results, and lets the teacher finalize the attendance record.

## 3.2 Product positioning

RIT-Sync Vision is:

- An **attendance assistant**, not an autonomous attendance authority.
- A **local Edge AI system**, not a cloud-first classroom video surveillance service.
- A **teacher-reviewed workflow**, not automatic absence detection.
- An **evidence-based process**, not a one-frame identity guess.

---

# 4. Goals and Success Outcomes

## 4.1 Product goals

1. Reduce the effort and time required for classroom roll-call.
2. Observe multiple students during one short capture window.
3. Improve recognition reliability through face-quality checks and multi-frame evidence.
4. Support open-set recognition so unknown people are not forced into registered identities.
5. Prevent duplicate attendance candidates.
6. Give teachers clear reason codes and control over finalization.
7. Continue recording authorized attendance events during network outages.
8. Minimize the collection and retention of biometric information.
9. Establish a measurable validation process before any pilot.

## 4.2 Success outcomes

The project should demonstrate that:

- A teacher can open an authorized session and initiate capture.
- The system can process multiple face observations from a classroom input.
- The system can identify registered candidates when evidence is sufficient.
- The system can return `UNKNOWN`, `NEEDS_REVIEW` or insufficient evidence.
- Repeated observations do not create duplicate candidates.
- A teacher can review, correct and finalize records.
- Offline records can be synchronized without loss or duplication.
- Raw classroom frames are not permanently stored.
- The complete workflow can be measured against manual roll-call.

## 4.3 Proposed validation targets

These are hypotheses from the presentation and must be tuned through testing. They are not guaranteed results or external standards.

| Area | Proposed target |
|---|---|
| Camera coverage | At least 95% usable face tracks per seat zone |
| Identity safety | No unreviewed wrong-ID finalization |
| Workflow time | Roster ready in approximately 60–120 seconds, to be benchmarked |
| Offline reliability | No lost or duplicate attendance events |
| Privacy | No raw classroom frames persisted |
| Teacher value | Teacher workflow time below manual roll-call |

---

# 5. Non-Goals

The following are not product goals for the current mini-project implementation:

- Automatically declaring students absent based only on non-detection.
- Removing the teacher from the attendance decision.
- Guaranteeing 100% face recognition accuracy.
- Claiming 100% protection against photo, video or replay attacks.
- Recording or storing classroom audio.
- Permanently retaining raw classroom images or video.
- Using face recognition as a general-purpose surveillance system.
- Starting with a microservices architecture.
- Building the final custom hardware before the software workflow has been validated.
- Claiming production readiness or legal compliance solely because the prototype works.
- Claiming patentability without a separate prior-art and legal assessment.

---

# 6. Users and Stakeholders

The presentation identifies teachers, students and institutions as target users.

## 6.1 Teacher

**Primary operational user.**

Needs to:

- Select the relevant class and attendance session.
- Start and stop an authorized capture window.
- See whether the camera, clock and model are ready.
- Review present candidates, uncertain matches and students not observed.
- Understand why a candidate needs review.
- Correct AI suggestions.
- Manually record attendance where necessary.
- Finalize attendance.
- View attendance history and session status.

## 6.2 Student

**Affected data subject and attendance participant.**

Needs:

- Clear information about the attendance process.
- Appropriate consent and privacy safeguards as required.
- A non-biometric attendance alternative.
- A way for an authorized teacher to correct an attendance error.
- Protection of face templates and attendance information.

The student is not required to operate the teacher dashboard.

## 6.3 Institution

**Governance and deployment stakeholder.**

Needs to:

- Approve the purpose and scope of use.
- Define authorized classes, devices and capture windows.
- Approve privacy, consent and retention arrangements.
- Review reliability and fairness evidence.
- Ensure a non-biometric fallback exists.
- Authorize pilots only after required reviews.

## 6.4 Administrator / Device operator

An administrator or authorized operator may configure teacher accounts, classes, device registration, capture permissions and system settings. The exact role separation and permission matrix must be confirmed by the team and institution.

---

# 7. Scope and Delivery Phases

## 7.1 Phase 1 — Software

Phase 1 develops the working software prototype using a laptop webcam and/or authorized recorded video.

### Included

- Teacher-facing web application.
- Authentication and role-controlled access.
- Class, subject and student management.
- Authorized capture session workflow.
- Camera input abstraction.
- Face detection and quality gate.
- Open-set 1:N recognition.
- Multi-frame face tracklets.
- Duplicate reconciliation.
- Attendance candidate generation.
- Teacher review and finalization.
- Local data storage.
- Offline event queue and synchronization foundation.
- Audit records.
- Privacy controls and testing.
- System health and fault states.
- Integration and validation reports.

### Phase 1 camera source

- Laptop webcam for live demonstration.
- Authorized recorded video for repeatable testing.
- Synthetic or consented test data where suitable.

### Phase 1 limitations

The laptop webcam is a development input. It does not prove that a selected production camera can cover all classroom seats. Camera geometry and seat-zone coverage must be measured separately.

## 7.2 Phase 2 — Hardware Development and Integration

Phase 2 integrates the software with a dedicated classroom device.

The presentation identifies these hardware elements:

- Camera and lens chosen through measurement.
- Edge compute selected after benchmarking.
- Secure key store, with TPM and secure boot as design considerations.
- Encrypted storage without raw frames.
- Network and power fault states.
- Visible capture indicator, including capture LED and mount.

Phase 2 must retain the Phase 1 application workflow and replace or extend the camera/Edge AI input adapter.

## 7.3 Out-of-scope until separately approved

- Institution-wide production rollout.
- Commercial product packaging.
- Multi-campus deployment.
- Cloud-based video storage.
- Hardware manufacturing at scale.
- Features not required by the reviewed workflow.

---

# 8. Core Product Principles

## 8.1 Bounded capture

Capture must:

- Start only with a valid authorized session permit.
- Have a configured, short duration.
- Be visible to the teacher and, in the hardware version, indicated physically.
- Stop at the configured end time or when the teacher stops it.
- Not continue as background or continuous surveillance.

The presentation proposes a 30–120 second capture window.

## 8.2 Local processing and frame disposal

- Raw frames are processed locally.
- Raw frames exist in memory only during processing.
- Raw frames are discarded after processing.
- No audio is captured.
- Raw classroom frames are not written to the database, sync queue, logs or ordinary storage.
- Review should use metadata and reason codes by default.

## 8.3 Open-set recognition

The enrolled roster is not assumed to contain every person visible to the camera. The recognition system must be able to return `UNKNOWN`.

## 8.4 Multi-frame evidence

The system uses face tracklets to connect observations across frames and gather evidence. A single low-quality frame must not force a match.

## 8.5 Teacher authority

The AI proposes; the teacher reviews and finalizes. Teacher corrections must be audited.

## 8.6 Offline resilience

An authorized offline session may produce provisional records. These remain provisional until successful synchronization and reconciliation.

---

# 9. End-to-End User Workflow

The corrected methodology in the presentation contains nine stages.

## Stage 1 — Open session

1. Teacher authenticates.
2. Teacher selects the class and relevant session context.
3. The application requests or validates a signed capture permit.
4. The permit defines the authorized session and expiry.
5. If the permit is missing, invalid or expired, capture must not start.

**Failure behaviour:** No automatic marking.

## Stage 2 — Health check

Check:

- Camera availability.
- Clock state.
- AI model availability.
- Storage readiness.
- Required session/permit state.

**Failure behaviour:** Show a visible fault state and prevent capture or automatic processing where safe operation cannot be established.

## Stage 3 — Capture

1. Start the bounded capture window.
2. Show capture status to the teacher.
3. Process frames locally.
4. Stop when the teacher ends the session or the configured window expires.

**Duration:** Configurable; proposed initial range is 30–120 seconds.

## Stage 4 — Quality gate

1. Detect faces.
2. Assess face size, blur, lighting, visibility and other supported quality factors.
3. Skip observations that do not meet the configured quality requirements.
4. Attach reason codes to rejected or uncertain observations.

**Failure behaviour:** Insufficient evidence; do not force recognition.

## Stage 5 — Match

1. Associate observations into face tracklets.
2. Generate face representations from usable observations.
3. Compare them against the authorized enrolled template set.
4. Apply open-set 1:N matching.
5. Evaluate the best match, threshold and best-versus-second-best margin.
6. Return a matched candidate, `UNKNOWN` or a review state.

## Stage 6 — Reconcile

1. Combine evidence across observations in a tracklet.
2. Identify repeated student candidates.
3. Prevent duplicate attendance candidates.
4. Detect conflicts, such as multiple tracks resolving to the same identity or inconsistent identity evidence.
5. Flag unresolved conflicts.

**Failure behaviour:** Send the conflict for teacher review; do not silently choose an identity.

## Stage 7 — Teacher review

The teacher reviews:

- Present candidates.
- Needs-review cases.
- Students not observed.
- Reason codes and available metadata.
- Potential conflicts and duplicate warnings.

The teacher may correct a suggestion or use the non-biometric/manual process.

## Stage 8 — Sync

- Save approved local events to a protected local queue.
- Keep records provisional while synchronization is pending.
- Synchronize when connectivity is restored.
- Retry safely without creating duplicates.
- Record synchronization errors and acknowledgement.

## Stage 9 — Finalize

- The teacher confirms the attendance record.
- Every edit and finalization is audited.
- Finalized records are stored by the backend.
- If synchronization is still pending, the local record must clearly show its provisional/pending state.

**Attendance definition from the presentation:** Attendance is based on being observed during the configured window, subject to teacher verification.

---

# 10. Attendance State Model

The system must keep AI observation states separate from final attendance states.

## 10.1 AI observation states

| State | Meaning | System action |
|---|---|---|
| `PRESENT_CANDIDATE` | Sufficient evidence suggests the enrolled student was observed | Present to teacher for confirmation |
| `NEEDS_REVIEW` | Evidence is uncertain, conflicting or requires human judgement | Show reason code and request teacher action |
| `NOT_OBSERVED` | The system did not obtain sufficient evidence that the student was observed | Leave unresolved; never convert automatically to absent |
| `UNKNOWN` | A detected face does not sufficiently match an enrolled identity | Do not assign a student ID |
| `INSUFFICIENT_EVIDENCE` | Face quality or observation count is inadequate | Retain as unresolved evidence |

The exact enum names may be adjusted in the implementation contract, but their meanings must remain consistent.

## 10.2 Final attendance states

| State | Meaning | Authority |
|---|---|---|
| `PRESENT` | Teacher confirms the student was present/observed | Teacher |
| `ABSENT` | Teacher or authorized institutional process records absence | Teacher / authorized authority |
| `UNRESOLVED` | Attendance has not been determined | Remains open |
| `EXCUSED` or other institutional states | Optional institution-defined status | Requires separate approval |

`NOT_OBSERVED` is not a final attendance state and is not equivalent to `ABSENT`.

## 10.3 State transition constraints

- AI may create candidates, not final attendance records.
- The teacher may accept, correct or leave a candidate unresolved.
- The backend must enforce the teacher's authorization for finalization.
- A candidate cannot be silently changed to a different student identity.
- Every correction must record actor, time, old value, new value and reason where applicable.
- A sync conflict must not silently overwrite a teacher-finalized record.

---

# 11. Functional Requirements

Priority definitions:

- **P0:** Required before a controlled pilot can be considered.
- **P1:** Required before production deployment.
- **P2:** Required before commercial deployment or broader productization.

The presentation uses P0/P1/P2 for prioritizing risk controls. The priorities below map requirements to those gates; they do not mean the prototype is automatically approved for a pilot.

## 11.1 Session and capture authorization

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-001 | P0 | The system shall require a valid capture permit before capture. | Invalid, missing or expired permits block capture. |
| FR-002 | P0 | The system shall use a bounded capture window. | Capture stops at configured expiry or teacher stop. |
| FR-003 | P0 | The system shall display capture state to the teacher. | Teacher can distinguish ready, capturing, stopped and failed states. |
| FR-004 | P0 | The system shall validate camera, clock and model health before capture. | Failed required checks prevent unsafe capture and show a fault. |
| FR-005 | P0 | The system shall not capture audio. | No audio input or audio storage is implemented. |
| FR-006 | P1 | The device shall support a visible physical capture indicator. | Hardware capture indicator is activated during capture. |

## 11.2 Camera input and frame lifecycle

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-010 | P0 | The software shall accept a supported local camera or authorized video input. | Test source produces frames for the pipeline. |
| FR-011 | P0 | The system shall handle camera disconnection and unreadable frames. | It reports a fault and does not generate unsupported attendance candidates. |
| FR-012 | P0 | The system shall process raw frames locally. | No raw frames are sent to a cloud service. |
| FR-013 | P0 | The system shall discard raw frames after processing. | Tests and storage inspection show no persistent raw frames. |
| FR-014 | P0 | The system shall not store raw frames in logs or the event queue. | Log and queue inspection shows no image/video payloads. |

## 11.3 Face detection and quality gate

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-020 | P0 | The system shall detect multiple faces in a frame. | Test scenes with multiple people return multiple face observations where visible. |
| FR-021 | P0 | The system shall produce face-location information for each detection. | Each detection has a valid bounded region and frame association. |
| FR-022 | P0 | The system shall evaluate face quality before recognition. | Quality decision is returned for each candidate observation. |
| FR-023 | P0 | The quality gate shall identify supported factors such as face size, blur, lighting and visibility. | Tests demonstrate rejection or review for known poor-quality inputs. |
| FR-024 | P0 | Poor-quality observations shall not be forced into identity matching. | Such observations return an insufficient-evidence/review outcome. |
| FR-025 | P1 | Quality failures shall include reason codes. | Teacher review can display the reason without exposing raw images by default. |

## 11.4 Face tracking and evidence aggregation

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-030 | P0 | The system shall link observations across multiple frames into tracklets. | A test sequence produces stable track associations for supported conditions. |
| FR-031 | P0 | Track IDs shall remain distinct from student identities. | A track cannot become a student identity without recognition evidence. |
| FR-032 | P0 | The system shall handle temporary face disappearance. | Track state follows documented timeout/association rules. |
| FR-033 | P0 | The system shall aggregate evidence across usable observations. | The recognition/decision layer receives evidence count and track context. |
| FR-034 | P0 | The system shall detect repeated observations of the same track. | Repeated frames do not create separate attendance candidates. |
| FR-035 | P1 | Conflicting track or identity evidence shall be flagged. | Conflicts are routed to teacher review. |

## 11.5 Open-set face recognition

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-040 | P0 | The system shall compare a usable face representation against authorized enrolled templates using 1:N matching. | A controlled test roster is searched using the approved comparison method. |
| FR-041 | P0 | The system shall support an explicit `UNKNOWN` result. | Unenrolled test subjects can produce `UNKNOWN`. |
| FR-042 | P0 | The system shall apply a configurable matching threshold. | Threshold is documented, versioned and testable. |
| FR-043 | P0 | The system shall evaluate the best-versus-second-best match margin. | Ambiguous close matches are not silently assigned. |
| FR-044 | P0 | The system shall route low-confidence or ambiguous results to review. | No weak match becomes a finalized identity without teacher action. |
| FR-045 | P1 | Model and threshold versions shall be traceable for evaluation. | Each result can be associated with the model/configuration version used. |
| FR-046 | P1 | Recognition performance shall be evaluated using appropriate 1:N metrics. | FPIR, FNIR, wrong-ID and review rates are reported. |

## 11.6 Reconciliation and attendance candidates

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-050 | P0 | The system shall reconcile repeated student candidates. | One session does not create multiple candidates for the same student without a flagged conflict. |
| FR-051 | P0 | The system shall produce `PRESENT_CANDIDATE`, `NEEDS_REVIEW` and `NOT_OBSERVED` outcomes. | All roster members can be represented without converting non-detection to absence. |
| FR-052 | P0 | The system shall include reason codes for uncertain or failed outcomes. | Teacher can see why review is needed. |
| FR-053 | P0 | The system shall not mark a student absent automatically because they were not detected. | Automated tests prove `NOT_OBSERVED` cannot become `ABSENT`. |
| FR-054 | P0 | The AI engine shall return suggestions and evidence, not final attendance records. | Only the authorized teacher workflow finalizes the record. |

## 11.7 Teacher review and finalization

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-060 | P0 | The teacher shall see the class roster and candidate categories. | Roster, candidates, review cases and not-observed cases are distinguishable. |
| FR-061 | P0 | The teacher shall be able to accept or correct a candidate. | Authorized changes are saved and reflected in the session. |
| FR-062 | P0 | The teacher shall be able to use a manual/non-biometric attendance path. | Attendance can be completed without face recognition. |
| FR-063 | P0 | The teacher shall explicitly finalize the session records. | No AI-only finalization path exists. |
| FR-064 | P0 | Teacher edits and finalization shall be audited. | Audit record includes actor, time, action and relevant before/after values. |
| FR-065 | P1 | Review shall use metadata and reason codes by default. | Raw frames are not required for normal review. |

## 11.8 Offline operation and synchronization

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-070 | P0 | The system shall support authorized offline session operation. | A valid offline permit allows the defined local workflow. |
| FR-071 | P0 | The system shall store provisional attendance events locally. | Events remain available after temporary network loss/restart, within the defined storage design. |
| FR-072 | P0 | The system shall maintain a protected local event queue. | Queue integrity checks detect invalid/tampered events. |
| FR-073 | P0 | Events shall have stable unique identifiers. | Repeated sync delivery does not create duplicates. |
| FR-074 | P0 | The system shall synchronize pending events when connectivity returns. | Pending events are acknowledged and status is updated. |
| FR-075 | P0 | The system shall not silently overwrite conflicting finalized records. | Conflicts are flagged for authorized resolution. |
| FR-076 | P1 | The system shall check permit expiry and counter/clock rollback conditions. | Expired or invalid offline authorization is rejected or flagged. |
| FR-077 | P1 | Pending and failed synchronization states shall be visible. | Teacher/operator can distinguish pending, synced and failed records. |

## 11.9 Privacy and security

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-080 | P0 | Raw frames shall not be persisted. | Storage, logs and queue are checked. |
| FR-081 | P0 | No audio shall be captured or stored. | Audio functionality is absent. |
| FR-082 | P0 | Face templates shall be encrypted at rest and access-controlled. | Authorized access and protection controls are tested. |
| FR-083 | P0 | Face templates shall be revocable/deletable through an authorized process. | Deletion/revocation workflow is tested. |
| FR-084 | P0 | A non-biometric alternative shall be available. | Teacher can use manual attendance. |
| FR-085 | P0 | Institutional and legal/privacy review shall precede any pilot. | Pilot gate contains documented approval. |
| FR-086 | P1 | Photo/replay attacks shall be tested using a documented PAD evaluation plan. | Results are reported by attack type; no blanket claim is made. |
| FR-087 | P1 | Event queues shall be signed and encrypted where supported by the device design. | Tamper checks and key handling are tested. |
| FR-088 | P1 | Clock rollback and permit expiry shall be handled. | Expired/replayed session authorization is rejected or flagged. |
| FR-089 | P1 | Device firmware and updates shall use secure boot/signed update controls in the hardware design. | Hardware implementation is verified separately. |
| FR-090 | P1 | Residual security limits shall be documented. | Threat/risk report states what is and is not protected. |

## 11.10 Device and system health

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-100 | P0 | The software shall show camera, clock, model, storage and network health where available. | Health check produces explicit status values. |
| FR-101 | P0 | The system shall expose visible fault states. | Camera, power, network or model faults are not hidden. |
| FR-102 | P1 | The hardware device shall use an appropriate secure key store and boot/update controls. | Selected hardware controls are bench-tested and documented. |
| FR-103 | P1 | The hardware shall provide a visible capture indicator. | Capture indicator state matches authorized capture state. |

---

# 12. Proposed Application Experience

The presentation establishes a teacher dashboard, backend and teacher-review workflow. The following screen list is a proposed software implementation of those requirements, not a claim that every screen is explicitly specified in the presentation.

## 12.1 Login / Authentication

- Teacher sign-in.
- Session expiry and logout.
- Role-appropriate access.
- Clear authentication errors.

## 12.2 Teacher Dashboard

- Today's classes and sessions.
- Total students and session summary.
- Present candidates, needs-review and not-observed counts.
- Pending synchronization count.
- Camera/model/system health indicators.

## 12.3 Classes and Subjects

- View and manage authorized classes.
- View subject/class associations.
- Access the roster for the selected class.

## 12.4 Student Management

- Add/edit/deactivate student records.
- Assign students to classes.
- View enrollment status.
- Access authorized face-template enrollment and revocation actions.

## 12.5 Face Registration

- Authorized enrollment workflow.
- Capture or import an allowed enrollment sample.
- Quality check the enrollment sample.
- Generate a template locally.
- Store the protected template.
- Avoid retaining the original image unless a separately approved policy requires it.

## 12.6 Session Setup

- Select class and session.
- Validate authorization/permit.
- Configure the bounded capture duration.
- Check camera, clock, model and storage health.
- Start or cancel the session.

## 12.7 Live Capture / AI Processing

- Show capture active/paused/stopped state.
- Show elapsed and configured duration.
- Show camera and model status.
- Show processing counts and fault states.
- Do not expose or persist raw classroom imagery beyond the active local processing view.

## 12.8 Attendance Review

- Present candidates.
- Needs-review cases.
- Not-observed students.
- Reason codes.
- Candidate conflicts.
- Teacher accept/correct/manual actions.
- Explicit finalize action.

## 12.9 Attendance Records

- View finalized records by class/date/session.
- Show provisional/sync-pending records distinctly.
- View audit history where authorized.

## 12.10 Reports and Analytics

- Attendance summaries.
- Session duration and workflow time.
- Recognition and review metrics for system evaluation.
- Export controls only where approved.

## 12.11 System Status and Settings

- Camera and model status.
- Storage and queue status.
- Network/sync state.
- Capture configuration.
- Authorized device/session settings.
- Privacy and security configuration.

---

# 13. System Architecture

## 13.1 Logical components

1. **Teacher dashboard:** Initiates sessions and presents review information.
2. **RIT-Sync backend:** Manages users, rosters, sessions, permits, candidates, teacher decisions, records and synchronization.
3. **Classroom camera:** Provides input during the authorized capture window.
4. **Edge perception:** Processes frames locally and discards raw frames.
5. **Identity engine:** Performs quality assessment, tracklet processing and open-set matching.
6. **Server reconciliation:** Checks event consistency and duplicate records.
7. **Teacher review:** Provides reason codes and finalization controls.
8. **Protected event queue:** Holds authorized provisional events for offline synchronization.

## 13.2 Phase 1 logical architecture

```text
Teacher Browser
    |
    | HTTPS / API (local development may use localhost)
    v
React Frontend
    |
    | Versioned REST API
    v
FastAPI Modular Monolith
    ├── Authentication and authorization
    ├── Users, students, classes and subjects
    ├── Capture sessions and permits
    ├── Attendance candidate/review/finalization
    ├── Attendance history and reporting
    ├── Audit logs
    ├── Offline event queue and synchronization
    └── AI integration adapter
            |
            | Internal Python interface
            v
        AI Engine
            ├── Camera/frame adapter
            ├── Face detection
            ├── Face quality gate
            ├── Face tracklets
            ├── Open-set 1:N matching
            ├── Reconciliation evidence
            └── Attendance candidate output

Backend Data Layer
    ├── Local database
    ├── Encrypted face-template storage
    ├── Provisional event queue
    └── Audit records
```

## 13.3 Phase 2 logical architecture

```text
Fixed Classroom Camera + Lens
             |
             v
      Edge Compute Device
             |
             ├── Local face detection
             ├── Quality assessment
             ├── Tracking and identity engine
             ├── Encrypted local storage
             ├── Secure key store
             ├── Capture indicator
             └── Protected event queue
                        |
                        | Network when available
                        v
                 RIT-Sync Backend
                        |
                        v
                 Teacher Dashboard
```

The final physical topology, protocols and device selection must be confirmed after camera geometry measurement and compute benchmarking.

---

# 14. Proposed Technical Implementation

The presentation defines the system behaviour and component roles but does not lock every software library. The following is a proposed implementation baseline for the mini-project. Team approval is required before dependency choices are treated as final.

| Layer | Proposed baseline | Purpose |
|---|---|---|
| Frontend | React + TypeScript | Teacher web interface |
| UI styling | Tailwind CSS | Consistent interface |
| Backend | Python + FastAPI | Application API and business logic |
| Computer vision | OpenCV | Camera and frame handling |
| Face detection | Model selected after evaluation | Multiple-face detection |
| Face recognition | Model selected after licensing/performance review | Face embeddings and matching |
| Local storage | SQLite | Phase 1 local persistence |
| Central database | PostgreSQL, if required by deployment | Centralized records |
| Version control | Git + GitHub | Collaboration and history |
| Testing | Python and frontend test tools selected by team | Unit, integration and system tests |
| Deployment packaging | Docker optional | Reproducible local setup |

### Architecture constraints

- Use a modular monolith in Phase 1; do not introduce microservices without an approved need.
- Keep the AI engine as an internal Python module initially.
- The backend owns persistence and business rules.
- The AI engine returns structured candidate evidence and never writes final attendance.
- The frontend consumes backend APIs and must not access the database directly.
- Keep the camera input adapter independent from the selected physical camera.

---

# 15. Conceptual Data Model

The following entities are a proposed data model derived from the workflow. Exact fields, identifiers, retention and database relationships must be finalized in the database design.

| Entity | Purpose | Data handling |
|---|---|---|
| `User` | Teacher/admin account | Protected account data |
| `Student` | Student roster and class association | Personal data; access-controlled |
| `Class` | Class/group information | Institution-controlled |
| `Subject` | Subject association | Institution-controlled |
| `FaceTemplate` | Protected biometric representation | Encrypted, revocable, access-controlled |
| `CaptureSession` | Authorized capture window and status | Session metadata |
| `CapturePermit` | Signed/validated session authorization | Protected authorization data |
| `FaceTracklet` | Temporary multi-frame association | Short-lived processing metadata |
| `Observation` | Quality and recognition evidence | Metadata; avoid raw frames |
| `AttendanceCandidate` | AI suggestion and reason codes | Provisional until teacher action |
| `AttendanceRecord` | Teacher-finalized attendance | Authoritative attendance record |
| `SyncEvent` | Offline event awaiting acknowledgement | Signed/protected, idempotent |
| `AuditEvent` | Teacher edits and critical actions | Append-oriented audit history |
| `DeviceHealth` | Camera/model/storage/network fault state | Operational metadata |

## 15.1 Data separation

- Raw frames are transient processing input, not a database entity.
- Face templates are biometric data and must be separately protected.
- AI candidates are not the same as finalized attendance records.
- Sync events are not the same as final server acknowledgement.
- Audit events should not contain raw images, face templates, secrets or unnecessary personal data.

---

# 16. AI Decision Logic Requirements

The presentation specifies the main decision stages and expected fail-safe behaviour.

| Stage | Expected behaviour | Failure outcome |
|---|---|---|
| Capture gate | Valid signed permit only | No automatic marking |
| Detection | Check face quality | Insufficient evidence |
| Tracklets | Link frames carefully | Send to review |
| Open-set 1:N | Apply threshold and margin | Return `UNKNOWN` |
| Reconcile | Prevent duplicate IDs | Flag conflict |
| Teacher | Show reason codes | Keep unresolved |

## 16.1 Recognition evaluation

Report at least:

- False Positive Identification Rate (FPIR).
- False Negative Identification Rate (FNIR).
- Wrong-ID rate.
- Teacher review rate.

Use suitable test protocols and keep test conditions documented. Include variation in lighting, focus, distance, face size and other supported factors.

## 16.2 No forced identity

The system must not select the nearest enrolled template merely because it is the closest available result. A match is acceptable only when the configured evidence and threshold conditions are met.

## 16.3 Reconciliation

The system must detect:

- Repeated observations of one track.
- Multiple tracks that may refer to the same enrolled student.
- Conflicting student identities within a track.
- Multiple candidate tracks that resolve to the same student.
- Unresolved or unknown observations.

A conflict must be visible to the teacher and remain unresolved until reviewed.

---

# 17. Privacy, Consent and Security

The presentation marks camera coverage, recognition, anti-spoofing and privacy/consent as critical before any pilot.

## 17.1 Privacy baseline

- Raw frames remain in memory only.
- No audio capture.
- Face templates are encrypted and revocable.
- Metadata-only review is the default.
- A non-biometric alternative is required.
- Legal/privacy review is required before any pilot.

## 17.2 Security baseline

- Photo/replay risks require presentation attack detection (PAD) testing and a manual fallback.
- Event queues should be signed and encrypted.
- Clock rollback protection should use a counter and permit expiry.
- Hardware should use secure boot and signed updates where supported.
- Residual limitations must be stated openly.

## 17.3 Important security distinctions

- A signed event does not prove that a face came from a genuine live camera capture.
- A valid permit does not prove that a student was physically present.
- A face match does not prove liveness.
- A successful PAD test against one attack type does not prove resistance to every attack.
- A high similarity score is not itself a calibrated probability of identity.

## 17.4 Pilot gate

No real student pilot should occur until the institution has approved the purpose, consent process, non-biometric alternative, data handling, access controls, retention/deletion process and relevant legal/privacy review.

---

# 18. Offline Operation and Synchronization

## 18.1 Expected behaviour

**When connected:**

1. Validate the authorized session.
2. Process locally.
3. Submit protected attendance events to the backend.
4. Reconcile and record server acknowledgement.
5. Show synchronized status.

**When disconnected:**

1. Validate that the offline permit is valid.
2. Process locally.
3. Save provisional events in the protected local queue.
4. Show that records are pending synchronization.
5. Do not silently treat provisional events as server-confirmed.

**When connectivity returns:**

1. Retry pending events.
2. Verify event integrity.
3. Use stable event IDs to prevent duplicate creation.
4. Reconcile conflicts.
5. Record acknowledgements.
6. Mark events synchronized only after successful acknowledgement.

## 18.2 Required protections

- Stable unique event identifiers.
- Signed and encrypted queue where supported.
- Retry-safe/idempotent processing.
- Permit expiry validation.
- Clock rollback detection.
- Conflict detection.
- Visible pending/failed/synced status.
- No raw frames in the queue.

---

# 19. Hardware Requirements for Phase 2

The presentation deliberately does not select a final camera or compute board. Selection must follow measurement and benchmarking.

| Component | Requirement | Selection method |
|---|---|---|
| Camera and lens | Must provide usable face observations across the classroom | Measure geometry and seat zones |
| Edge compute | Must run perception and identity processing locally | Benchmark candidate devices |
| Secure key store | Protect device identity and relevant keys | Confirm TPM/secure key support |
| Storage | Encrypted; no raw frames | Validate capacity, endurance and protection |
| Network/power | Faults must be visible and recoverable | Test network/power interruption |
| Indicator | Visible capture LED and suitable mount | Verify against capture state |

## 19.1 Camera geometry

Before camera selection:

- Measure classroom dimensions.
- Map all seat zones.
- Estimate face size and visibility at each seat.
- Evaluate occlusion and viewing angle.
- Check lighting and focus conditions.
- Test the proposed camera/lens combination.
- Record coverage gaps.

Do not claim classroom coverage based only on a single front-row demonstration.

## 19.2 Edge compute benchmark

Measure:

- Model load and startup time.
- Frame processing speed.
- Memory use.
- Thermal behaviour.
- Power draw.
- Sustained operation.
- Offline storage reliability.

The selected compute device must be based on these results rather than a theoretical specification alone.

---

# 20. Performance and Reliability Requirements

The following are proposed project targets from the presentation, not contractual guarantees.

## 20.1 Performance

- Target roster preparation time: approximately 60–120 seconds, to be benchmarked.
- Capture window: configurable; initial proposal 30–120 seconds.
- The device should report camera/model health before capture.
- The system should not sacrifice identity safety merely to meet a speed target.

## 20.2 Reliability

- No lost attendance events during tested offline recovery.
- No duplicate attendance records after repeated synchronization.
- No unreviewed wrong-ID finalization.
- Camera/model/network/storage failures must create visible states.
- A failed or interrupted session must not silently create final absences.

## 20.3 Coverage

- Measure every seat zone.
- Report usable face-track coverage by zone.
- Investigate zones below the proposed target.
- A coverage gap must result in a limitation/fallback, not an inferred absence.

---

# 21. Validation Plan and Release Gates

The presentation proposes six validation activities.

## A — Desk model

Purpose:

- Create a classroom layout model.
- Identify camera placement options.
- Estimate seat coverage and viewing angles.
- Record geometry assumptions.

Exit evidence:

- Classroom layout and proposed camera geometry.

## B — Camera geometry

Purpose:

- Test actual camera/lens placement.
- Measure usable face size and visibility per seat zone.
- Identify blind spots and occlusion.

Exit evidence:

- Coverage map and per-zone observations.

## C — Shadow test

Purpose:

- Run the system in observation/shadow mode.
- Compare AI candidates with a separately established human reference.
- Do not use unverified AI suggestions as authoritative attendance.

The presentation identifies an adult pilot before a student pilot. Any such testing requires applicable approval and consent.

Exit evidence:

- Detection, identity, review and timing results.
- Error cases and limitations.

## D — Fault injection

Test:

- Camera disconnect.
- Clock fault or rollback.
- Model unavailable.
- Network loss.
- Power interruption where applicable.
- Invalid/expired permit.
- Duplicate or replayed event.
- Synchronization retry.
- Storage failure.

Exit evidence:

- Fault matrix with expected and observed behaviour.
- No lost or duplicated events in the tested cases.
- Correct visible fault states.

## E — Adult pilot

A controlled adult pilot may be considered only after required institutional/privacy review and appropriate consent. Use it to validate camera geometry, workflow and model behaviour before student testing.

Exit evidence:

- Approval record.
- Consent/process documentation.
- Test results.
- Known limitations and corrective actions.

## F — Student pilot

Only after the preceding gates are passed and the institution authorizes it.

Requirements:

- Approved purpose and process.
- Non-biometric alternative.
- Appropriate notice/consent and governance.
- Data protection and deletion process.
- Teacher review and correction process.
- Monitoring and incident response.

The presentation does not authorize a student pilot by itself.

---

# 22. Release Readiness Gates

## P0 — Before any pilot

The presentation marks the following as critical:

- Measure camera coverage for every seat.
- Validate open-set 1:N recognition with `UNKNOWN`.
- Test anti-spoofing by attack type; make no 100% claim.
- Complete privacy/consent review and provide a fallback.
- Ensure teacher review and finalization.
- Ensure raw frames are not persisted.

## P1 — Before production

- Device trust controls.
- Secure key storage and update controls.
- Reliable permit expiry and clock handling.
- Tested offline queue and synchronization.
- Measured recognition and coverage performance.
- Documented fault handling and residual risks.

## P2 — Before commercial use

- Further device hardening and operational controls.
- Broader validation and monitoring.
- Further patent/prior-art and product assessment.
- Commercial deployment requirements, support and maintenance planning.

A prototype passing its own demo is not equivalent to passing P0, P1 or P2.

---

# 23. Risks and Mitigations

| Risk | Severity in presentation | Mitigation / required response |
|---|---|---|
| Inadequate camera coverage | Critical | Measure every seat; produce a coverage map before pilot |
| Wrong identity match | Critical | Open-set 1:N, threshold and margin, teacher review |
| Unknown person forced into roster | Critical | Explicit `UNKNOWN` result |
| Poor face quality | Critical | Quality gate and insufficient-evidence state |
| Not detected interpreted as absent | Critical | Separate `NOT_OBSERVED` from `ABSENT` |
| Photo/video replay | Critical | PAD evaluation by attack type and manual fallback |
| Privacy/consent failure | Critical | Non-biometric alternative and legal/privacy review |
| Network outage | High | Valid offline permits, protected queue, later sync |
| Device tampering | High | Signed events, secure key storage, secure boot and updates |
| Clock rollback | High | Counter and permit expiry checks |
| Patent overlap | High | Concept has crowded prior art; seek only a narrow, tested mechanism |

---

# 24. Patent and Novelty Position

The presentation states that the broad classroom face-recognition attendance concept has crowded prior art, including referenced US patents and a 2026 paper.

The presentation identifies a possible narrower lead:

- Camera-quality coverage controller.

This is only a research direction, not a claim of novelty or patentability. Any patent work requires a separate, professional prior-art search and legal assessment.

The product should be developed for its practical value even if no patent is pursued or granted.

---

# 25. Phase 1 Implementation Roadmap

This roadmap organizes the presentation's stages into software delivery order. It does not assign fixed calendar dates.

| Step | Workstream | Main output |
|---|---|---|
| 0 | Research | Model, privacy, standards and prior-art review |
| 1 | Geometry | Classroom layout and coverage prototype |
| 2 | Recognition | Detection, quality, open-set recognition and tracklets |
| 3 | Integration | Frontend, backend, AI and teacher workflow connected |
| 4 | Offline + security | Protected queue, sync, permits, privacy and fault testing |
| 5 | Shadow pilot | Controlled evaluation under approved conditions |
| 6 | Production gate | Evidence-based P0/P1 review and decision |

## 25.1 Phase 1 implementation sequence

1. Finalize system architecture and contracts.
2. Set up the monorepo and modular monolith.
3. Implement authentication and student/class records.
4. Implement authorized session and permit handling.
5. Implement camera input adapter for webcam/video.
6. Implement face detection and face quality gate.
7. Implement face templates and open-set recognition.
8. Implement multi-frame tracklets.
9. Implement reconciliation and attendance candidates.
10. Implement teacher review and finalization.
11. Implement protected local event queue and sync.
12. Implement audit and privacy controls.
13. Integrate all modules.
14. Run functional, performance, fault and privacy tests.
15. Document measured results and limitations.

---

# 26. Roles and Ownership

The project uses a modular monolith and one repository. Ownership boundaries reduce conflicting implementation work.

| Member | Primary ownership | Main deliverables |
|---|---|---|
| Paul Bryton Raj | AI engine and system integration | Detection, quality, recognition, tracking, decision evidence, AI tests, architecture and integration |
| Pon Vijayalakshmi | Backend and data | FastAPI, database, student/class/session APIs, records, offline queue, sync and audit |
| Rakesh Anand | Frontend | React UI, navigation, dashboard, capture/review pages, management screens and API integration |

### Cross-team constraints

- Paul's AI engine must not write final attendance records directly.
- Vijayalakshmi owns backend persistence and authoritative attendance records.
- Rakesh's frontend must use backend APIs rather than direct database access.
- Shared API schemas and status meanings must be agreed before implementation.
- Cross-owner file changes require coordination.
- All team members participate in integration and system validation.

---

# 27. Acceptance Criteria for the Complete Product

A Phase 1 software demonstration is acceptable when all the following can be shown:

1. A teacher can authenticate.
2. The teacher can select an authorized class/session.
3. The application validates the capture permit.
4. The system performs the required health check.
5. The teacher can start a bounded webcam/video capture session.
6. Multiple faces can be detected where visible.
7. Poor-quality observations are rejected or flagged.
8. Recognized identities are based on open-set matching against enrolled templates.
9. Unknown and ambiguous observations remain unknown or require review.
10. Multi-frame tracking reduces repeated observations.
11. Duplicate candidates are prevented or flagged.
12. The system creates present candidates, needs-review cases and not-observed states.
13. Not-observed is never automatically changed to absent.
14. The teacher can correct and finalize attendance.
15. Teacher changes are recorded in an audit trail.
16. Raw frames are not permanently stored.
17. The local queue can retain authorized provisional events during an outage.
18. Synchronization can be retried without creating duplicate events.
19. Faults are visible and do not silently produce attendance.
20. Tests, measured performance and known limitations are documented.

Passing these criteria demonstrates a working software prototype. It does not, by itself, establish production readiness or permission for a real student pilot.

---

# 28. Open Decisions

The presentation intentionally leaves several implementation details to measurement and research. Resolve these before locking the implementation.

| Decision | Required owner(s) | Evidence needed |
|---|---|---|
| Camera model, lens and location | Paul + team | Geometry and seat-zone coverage tests |
| Edge compute device | Paul + team | Performance, memory, power and thermal benchmark |
| Face detector model | Paul | Accuracy/speed and licensing comparison |
| Face recognition model | Paul | Open-set 1:N evaluation and licensing comparison |
| Threshold and margin | Paul | Validation data and error trade-off |
| Face tracking method | Paul | Multi-frame association tests |
| Enrollment process | Paul + Vijayalakshmi + institution | Consent, quality, revocation and template protection |
| Offline permit issuer and key management | Vijayalakshmi + system lead | Security design and device trust model |
| Database and retention details | Vijayalakshmi + institution | Data model and retention/deletion policy |
| User role/permission matrix | Vijayalakshmi + Rakesh | Approved user stories |
| Capture indicator behaviour | Hardware team | Device design and testing |
| Pilot authorization | Institution | Formal approval and privacy/legal review |

Do not silently invent answers to these decisions. Record the chosen solution and rationale in the relevant design document.

---

# 29. Assumptions and Constraints

## Assumptions

- The initial software prototype can use a laptop webcam and authorized videos.
- The teacher is the final decision-maker.
- The enrolled roster and templates are managed through an authorized process.
- The software will use an institution-approved class roster.
- The backend can store provisional local events and synchronize later.
- The hardware camera and compute device are selected only after measurement and benchmarking.

## Constraints

- The system cannot infer absence from camera non-detection.
- Far-row face size and camera geometry may limit recognition.
- Recognition results depend on camera quality, environment and model performance.
- Anti-spoofing is not guaranteed.
- Biometric processing requires privacy, consent and institutional review.
- Offline records remain provisional until reconciliation.
- The prototype's performance must be measured, not assumed.

---

# 30. Source References from the Presentation

The following references are reproduced from slides 12–13 of the supplied presentation. They are the presentation's bibliography, not an independent verification of every citation.

| Ref. | Source as listed in presentation |
|---|---|
| R1 | Mao, Li, Yin (2014). “Who missed the class? Unifying multi-face detection, tracking and recognition in videos.” IEEE ICME. DOI: 10.1109/ICME.2014.6890334 |
| R2 | Hoo & Ibrahim (2019). “Biometric-Based Attendance Tracking System for Education Sectors: Literature Survey on Hardware Requirements.” Journal of Sensors, 7410478. |
| R3 | “Student attendance with face recognition (LBPH or CNN): Systematic literature review.” Procedia Computer Science 216 (2023), 31–38. |
| R4 | Abiodun et al. (2026). “LaED: lightweight, edge-aware, explainable model for privacy-preserving facial attendance.” Scientific Reports 16, 15215. |
| R5 | US Patent 11,763,605 B2 (2023). “Synchronized online/offline clock in management.” |
| R6 | US Patent 11,694,482 B2 (2023). “Information processing device and attendance state management method.” |
| R7 | NIST (2017). “Identifying Faces in Video Images is Major Challenge, NIST Report Shows.” |
| R8 | NIST VQiPS (2024). “Target Size.” |
| R9 | “Low-resolution face recognition: Review, challenges and research directions.” Computers & Electrical Engineering 120 (2024), 109846. |
| R9a | “Peepers & Pixels: Human Recognition Accuracy on Low Resolution Faces.” IEEE FG 2025. |
| R9b | “Tiny Faces, Big Trouble: Evaluating Super-Resolution for Face Recognition.” IEEE FG 2025. |
| R10 | NIST FRTE — 1:N Identification (FPIR / FNIR). |
| R11 | NIST FRTE 1:1 & Demographic Effects; NISTIR 8280, NISTIR 8429. |
| R12 | ISO/IEC 19795-1:2021 and 19795-10:2024 — biometric performance testing and demographic variation. |
| R13 | ISO/IEC 30107-1:2023 — Biometric presentation attack detection, Part 1: Framework. |
| R14 | ISO/IEC 30107-3:2023 — PAD, Part 3: Testing and reporting. |
| R15 | “Survey on Anti-Spoofing Methods for Facial Recognition with RGB Cameras of Generic Consumer Devices.” Journal of Imaging 6(12), 139 (2020). |
| R16 | NIST SP 800-193 (2018). “Platform Firmware Resiliency Guidelines.” |
| R17 | Galligan et al. (2020). “Cameras in the Classroom: Facial Recognition Technology in Schools.” University of Michigan STPP. |
| R18 | Selwyn et al. (2020). “Facial recognition technology in schools: critical questions and concerns.” Learning, Media & Technology. |
| R19 | Aposika (2026). “Role of biometric systems in enhancing student attendance tracking in tertiary institutions.” Discover Education 5, 386. |
| R20 | Government of India. IT (Reasonable Security Practices & Procedures and SPDI) Rules, 2011. |
| R21 | MeitY. DPDP Act enforcement timeline notification (Nov 2025); DPDP Rules, 2025. |
| R22 | Hakimi, Eynon, Murphy (2021). “Ethics of Using Digital Trace Data in Education.” Review of Educational Research. |
| R23 | Regenscheid (2018). NIST SP 800-193, “Platform Firmware Resiliency Guidelines.” |
| R24 | Jack et al. (2026). “Multi-facet facial recognition model for institutional attendance during examinations.” Discover AI. |
| R25 | NIST (2010). “Quantifying How Lighting and Focus Affect Face Recognition Performance.” NISTIR 7674. |
| R26 | NIST (2014). “Identifying Face Quality and Factor Measures for Video.” |

**Reference note from the presentation:** Standards describe testing frameworks and do not guarantee compliance. The presentation states that its 2026 results are author-reported and not independently reproduced. Its patent note is not legal advice and is not an exhaustive patentability search.

---

# 31. Glossary

| Term | Meaning in RIT-Sync Vision |
|---|---|
| Edge AI | AI processing performed on or near the classroom device rather than requiring continuous cloud processing |
| Face detection | Finding face regions in an image/frame |
| Face recognition | Comparing a detected face representation with enrolled templates |
| Open-set 1:N | Searching across multiple enrolled identities while allowing the result to be unknown |
| `UNKNOWN` | No enrolled identity meets the configured matching conditions |
| Tracklet | A sequence of face observations associated across multiple frames |
| Quality gate | Check that a face observation is usable before recognition |
| FPIR | False Positive Identification Rate |
| FNIR | False Negative Identification Rate |
| PAD | Presentation Attack Detection; tests for attacks such as photo or replay presentation |
| Capture permit | Authorization for a defined capture session and time window |
| Protected event queue | Local queue holding protected events while waiting for synchronization |
| Provisional record | Locally held record that has not yet completed required synchronization/reconciliation |
| Teacher finalization | Authorized teacher decision that makes the attendance record final |
| Not observed | Insufficient evidence that the student was observed; not equivalent to absent |

---

# 32. Final Product Statement

RIT-Sync Vision is a confidence-aware classroom attendance assistant that uses locally processed, bounded camera input, open-set face recognition and multi-frame evidence to propose attendance candidates. It protects against forced identity decisions through quality checks, `UNKNOWN` results, duplicate reconciliation and teacher review. It is designed to work through network interruptions using protected provisional events and later synchronization, while avoiding permanent storage of raw classroom frames.

**The system's most important rule remains:**

# AI proposes. The teacher finalizes.
# NOT OBSERVED ≠ ABSENT.

