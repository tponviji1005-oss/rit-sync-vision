# RIT-SYNC VISION
# PAUL BRYTON RAJ — DETAILED DEVELOPMENT PLAN

ROLE: AI & SYSTEM LEAD
PHASE: PHASE 1 — SOFTWARE DEVELOPMENT

PRIMARY OWNERSHIP:
- System Architecture
- AI Engine Development
- Computer Vision
- Face Detection
- Face Quality Assessment
- Face Recognition
- Open-Set Matching
- Multi-Frame Face Tracking
- Attendance Decision Logic
- AI Evaluation and Testing
- AI Privacy and Security
- Backend-AI Integration
- Overall System Integration

==================================================
1. YOUR MAIN OBJECTIVE
==================================================

Build the complete AI engine that powers RIT-Sync Vision.

The AI engine must process classroom camera input, detect multiple faces, evaluate face quality, track faces across multiple frames, recognize registered students and generate attendance suggestions.

The system must handle unknown people and uncertain recognition results without forcing an incorrect identity.

The AI engine must communicate with Vijayalakshmi's backend through an agreed interface.

The final attendance decision must always belong to the teacher.

YOUR FINAL GOAL:

Develop a working AI system that can receive classroom camera input, process multiple faces, identify registered students where evidence is sufficient, detect unknown people, track repeated observations and generate structured attendance suggestions.


==================================================
2. YOUR WORKING DIRECTORY
==================================================

You are primarily responsible for:

rit-sync-vision/
│
├── ai_engine/
│   │
│   ├── detection/
│   │   ├── face_detector.py
│   │   └── face_quality.py
│   │
│   ├── recognition/
│   │   ├── face_encoder.py
│   │   ├── face_matcher.py
│   │   └── unknown_detector.py
│   │
│   ├── tracking/
│   │   ├── face_tracker.py
│   │   └── track_manager.py
│   │
│   ├── quality_check/
│   │   ├── blur_check.py
│   │   ├── lighting_check.py
│   │   └── face_visibility.py
│   │
│   ├── decision_engine/
│   │   ├── attendance_decision.py
│   │   ├── confidence.py
│   │   └── duplicate_checker.py
│   │
│   ├── privacy/
│   │   ├── frame_handler.py
│   │   └── template_protection.py
│   │
│   ├── models/
│   │   └── README.md
│   │
│   ├── tests/
│   │
│   ├── pipeline.py
│   ├── camera_input.py
│   └── requirements.txt
│
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── AI_WORKFLOW.md
│   ├── AI_MODEL_EVALUATION.md
│   └── INTEGRATION_REPORT.md
│
└── shared/
    ├── schemas/
    └── constants/

IMPORTANT:

You own ai_engine/.

Do not independently modify the frontend or Vijayalakshmi's backend implementation.

Changes to shared contracts, root configuration and documentation must be coordinated.


==================================================
3. DEVELOPMENT PHASES
==================================================

PHASE A — SYSTEM ARCHITECTURE

OBJECTIVE:

Understand and establish how all parts of RIT-Sync Vision will communicate.

TASKS:

1. Study the complete project PRD and PPT.
2. Finalize the software architecture.
3. Define the relationship between frontend, backend and AI engine.
4. Define the AI processing workflow.
5. Define the input and output formats of the AI engine.
6. Decide how camera input reaches the AI pipeline.
7. Define the responsibilities of individual AI modules.
8. Coordinate database and API requirements with Vijayalakshmi.
9. Coordinate AI dashboard requirements with Rakesh.
10. Document all important technical decisions.

EXPECTED DELIVERABLES:

- System architecture diagram.
- AI processing flowchart.
- AI module responsibility document.
- AI input/output contract.
- Technology and model selection report.

ACCEPTANCE CONDITION:

All three developers must understand how their modules connect before major implementation begins.


==================================================
PHASE B — CAMERA INPUT AND CAPTURE
==================================================

OBJECTIVE:

Develop a camera input system that can receive classroom video frames.

PHASE 1 INPUT SOURCES:

- Laptop webcam.
- Recorded classroom videos.
- Authorized sample videos.

TASKS:

1. Implement camera initialization.
2. Read video frames using OpenCV.
3. Handle camera initialization errors.
4. Handle camera disconnection.
5. Support recorded video input.
6. Support start and stop capture.
7. Process frames during a configured capture window.
8. Release camera resources correctly.
9. Ensure frames are processed in memory.
10. Discard raw frames after processing.

CAPTURE WINDOW:

Use a configurable window between 30 and 120 seconds, as proposed in the PPT.

CAMERA HEALTH CHECK:

- Camera availability.
- Frame availability.
- Frame dimensions.
- Frame processing status.
- Capture session status.

IMPORTANT:

The laptop webcam is only a temporary camera source for Phase 1.

Design the camera input module so that a dedicated classroom camera can replace it during Phase 2.

EXPECTED FILES:

- camera_input.py
- pipeline.py

EXPECTED DELIVERABLE:

A working camera input module that continuously provides frames to the AI pipeline without permanently storing raw classroom footage.


==================================================
PHASE C — MULTIPLE FACE DETECTION
==================================================

OBJECTIVE:

Detect multiple faces in a single classroom frame.

TASKS:

1. Research suitable face detection models.
2. Compare detection speed and accuracy.
3. Test detection with multiple faces.
4. Identify face bounding boxes.
5. Calculate detection confidence.
6. Handle partially visible faces.
7. Handle faces at different distances.
8. Handle different face angles.
9. Return structured detection results.
10. Handle frames with no detected faces.

TEST CONDITIONS:

- Front-row students.
- Middle-row students.
- Back-row students.
- Multiple faces in one frame.
- Partially hidden faces.
- Different lighting conditions.
- Different face sizes.

IMPORTANT:

Camera coverage is a major project risk.

The PPT requires measuring every seat and validating usable face tracks per seat zone.

Do not assume that every student can be recognized just because the camera detects faces.

EXPECTED FILE:

detection/face_detector.py

EXPECTED DELIVERABLE:

A working multiple-face detection system that returns face locations and detection information for each frame.


==================================================
PHASE D — FACE QUALITY ASSESSMENT
==================================================

OBJECTIVE:

Determine whether a detected face contains sufficient information for reliable recognition.

TASKS:

1. Check face size.
2. Check image blur.
3. Check lighting conditions.
4. Check face visibility.
5. Check face angle.
6. Identify low-quality detections.
7. Generate quality scores.
8. Define minimum quality requirements.
9. Reject unusable face observations.
10. Return reason codes for failed quality checks.

POSSIBLE REASON CODES:

- FACE_TOO_SMALL
- IMAGE_BLUR
- POOR_LIGHTING
- FACE_OCCLUDED
- FACE_ANGLE_UNSUITABLE
- INSUFFICIENT_QUALITY

IMPORTANT:

Never force face recognition when the input quality is insufficient.

Such cases must be sent for teacher review or remain unresolved.

EXPECTED FILES:

detection/face_quality.py
quality_check/

EXPECTED DELIVERABLE:

A face quality checking module that filters unusable face observations before recognition.


==================================================
PHASE E — FACE RECOGNITION
==================================================

OBJECTIVE:

Identify registered students by comparing detected face representations with authorized enrolled face templates.

TASKS:

1. Research suitable face recognition models.
2. Compare candidate models.
3. Verify model licensing and usage restrictions.
4. Test recognition performance.
5. Generate numerical face representations.
6. Compare detected representations with enrolled templates.
7. Calculate similarity scores.
8. Implement configurable matching thresholds.
9. Compare the best and second-best matches.
10. Return a possible identity only when the evidence is sufficient.

OPEN-SET RECOGNITION:

The system must not assume that every detected face belongs to a registered student.

It must be able to return:

- MATCHED
- UNKNOWN
- NEEDS_REVIEW
- INSUFFICIENT_QUALITY

UNKNOWN DETECTION:

If the best matching result does not satisfy the configured threshold or matching margin, return UNKNOWN or NEEDS_REVIEW.

Never force an identity.

IMPORTANT:

Recognition confidence is not automatically the probability that a person is correctly identified.

Calibrate and evaluate the matching thresholds using appropriate test data.

EXPECTED FILES:

recognition/face_encoder.py
recognition/face_matcher.py
recognition/unknown_detector.py

EXPECTED DELIVERABLE:

A working face recognition module that compares enrolled templates and supports unknown identity detection.


==================================================
PHASE F — MULTI-FRAME FACE TRACKING
==================================================

OBJECTIVE:

Improve face observation by tracking individuals across consecutive video frames.

WHY THIS IS IMPORTANT:

One frame may contain:
- A blurred face.
- A partially hidden face.
- A face turned away from the camera.
- An unclear recognition result.

Multiple observations can provide better evidence.

TASKS:

1. Receive face detections from consecutive frames.
2. Assign temporary tracking IDs.
3. Associate detections belonging to the same visible person.
4. Maintain tracking information.
5. Handle temporary face disappearance.
6. Collect quality information across observations.
7. Combine recognition evidence.
8. Detect repeated observations.
9. Prevent duplicate attendance candidates.
10. Remove temporary tracking information after the session.

IMPORTANT:

A tracking ID is not a student identity.

The same track must not automatically be treated as a confirmed student without sufficient recognition evidence.

EXPECTED FILES:

tracking/face_tracker.py
tracking/track_manager.py

EXPECTED DELIVERABLE:

A multi-frame tracking module that connects repeated face observations and passes consolidated evidence to the recognition and decision modules.


==================================================
PHASE G — ATTENDANCE DECISION ENGINE
==================================================

OBJECTIVE:

Convert AI processing results into structured attendance suggestions.

This is one of the most important modules in the complete system.

TASKS:

1. Receive face detection results.
2. Receive face quality results.
3. Receive tracking information.
4. Receive recognition results.
5. Evaluate confidence.
6. Evaluate matching margin.
7. Aggregate multi-frame evidence.
8. Check repeated student candidates.
9. Prevent duplicate attendance candidates.
10. Generate attendance suggestions.
11. Attach reason codes.
12. Send results to the backend.

THREE MAIN ATTENDANCE STATES:

1. PRESENT CANDIDATE

The system has sufficient evidence that the student was observed during the configured capture window.

2. NEEDS REVIEW

The identity is uncertain, the evidence conflicts, or further teacher verification is required.

3. NOT OBSERVED

The system has insufficient evidence to confirm that the student was observed.

NON-NEGOTIABLE RULE:

NOT OBSERVED DOES NOT MEAN ABSENT.

The AI engine must never automatically finalize an absence.

The backend stores the attendance records, and the teacher makes the final decision.

EXPECTED FILES:

decision_engine/attendance_decision.py
decision_engine/confidence.py
decision_engine/duplicate_checker.py

EXPECTED DELIVERABLE:

A functioning attendance decision engine that generates teacher-reviewable attendance candidates.


==================================================
PHASE H — AI AND BACKEND INTEGRATION
==================================================

OBJECTIVE:

Connect the AI engine with Vijayalakshmi's FastAPI backend.

TASKS:

1. Package the AI engine as an importable Python module.
2. Define the AI pipeline entry point.
3. Define the backend-to-AI input contract.
4. Define the AI-to-backend output contract.
5. Define error handling.
6. Return structured JSON-compatible results.
7. Handle failed recognition.
8. Handle unavailable models.
9. Handle camera errors.
10. Test the complete API integration.

PROPOSED AI OUTPUT FORMAT:

{
  "session_id": "SESSION_ID",
  "observations": [
    {
      "track_id": "TRACK_001",
      "candidate_student_id": "STUDENT_ID",
      "match_state": "MATCHED",
      "confidence": 0.96,
      "reason_codes": [],
      "evidence_count": 5
    },
    {
      "track_id": "TRACK_002",
      "candidate_student_id": null,
      "match_state": "UNKNOWN",
      "confidence": 0.31,
      "reason_codes": ["LOW_MATCH_CONFIDENCE"],
      "evidence_count": 3
    }
  ]
}

This is a proposed interface, not a finalized contract.

Coordinate with Vijayalakshmi before implementation.

IMPORTANT:

- AI engine does not directly write attendance records.
- AI engine does not directly modify student records.
- AI engine does not finalize attendance.
- Backend controls persistence and business rules.
- Teacher controls final attendance confirmation.

EXPECTED DELIVERABLE:

A working integration between FastAPI and the internal AI engine.


==================================================
PHASE I — PRIVACY AND SECURITY
==================================================

OBJECTIVE:

Implement privacy-conscious AI processing and support the system security design.

TASKS:

1. Process raw frames in memory.
2. Discard raw frames after processing.
3. Prevent accidental frame storage.
4. Protect face templates.
5. Avoid storing biometric data in ordinary logs.
6. Ensure authorized session context is passed to the AI pipeline.
7. Validate that processing occurs only within an authorized capture session.
8. Define temporary-data deletion.
9. Review AI module dependencies.
10. Document security limitations.

ATTACK SCENARIOS TO TEST:

- Photograph replay.
- Video replay.
- Poor-quality input.
- Unauthorized camera access.
- Unauthorized enrollment data access.
- Tampered input or event metadata.

IMPORTANT:

A signed capture permit does not automatically prove genuine camera capture.

Presentation attack detection must be evaluated separately.

Do not claim 100% spoof prevention.

COORDINATION:

Vijayalakshmi owns backend authentication, authorization, encrypted persistence and server-side security.

Paul owns AI-side privacy, frame lifecycle, AI model risks and technical integration.

EXPECTED DELIVERABLE:

A documented and tested AI privacy and security implementation.


==================================================
PHASE J — AI EVALUATION AND TESTING
==================================================

OBJECTIVE:

Evaluate the AI engine under realistic classroom conditions.

TEST 1 — FACE DETECTION

- Multiple faces.
- Different seating distances.
- Different lighting conditions.
- Different face sizes.
- Partially hidden faces.

TEST 2 — FACE QUALITY

- Blurred faces.
- Poor lighting.
- Face angle variation.
- Occlusion.
- Small faces.

TEST 3 — FACE RECOGNITION

- Registered students.
- Unknown individuals.
- Similar-looking individuals.
- Low-confidence matches.
- Ambiguous matches.

TEST 4 — TRACKING

- Consecutive frames.
- Temporary disappearance.
- Repeated detection.
- Track association errors.
- Duplicate candidate prevention.

TEST 5 — ATTENDANCE DECISION

- Correct present candidate.
- Unknown person.
- Low-confidence recognition.
- Insufficient observations.
- Duplicate student candidates.
- NOT OBSERVED handling.

TEST 6 — PRIVACY

- Raw frames are not permanently stored.
- Temporary data is removed.
- Templates receive appropriate protection.
- Logs do not contain sensitive biometric information.

METRICS TO EVALUATE:

- Face detection rate.
- Usable face-track coverage per seat zone.
- False Positive Identification Rate (FPIR).
- False Negative Identification Rate (FNIR).
- Wrong-ID rate.
- Recognition review rate.
- Duplicate candidate rate.
- Processing time per frame.
- Total attendance processing time.

IMPORTANT:

The PPT proposes the following validation targets:

- At least 95% usable face tracks per seat zone.
- No unreviewed wrong-ID finalization.
- Approximately 60–120 seconds for roster preparation.
- No lost or duplicate events during offline operation.

These are proposed targets, not guaranteed results.

Measure them and report actual results.

EXPECTED DELIVERABLE:

AI evaluation report with test conditions, measured results, limitations and model comparison.


==================================================
PHASE K — COMPLETE SYSTEM INTEGRATION
==================================================

OBJECTIVE:

Ensure the frontend, backend, database and AI engine work together as one application.

YOUR RESPONSIBILITIES:

1. Coordinate frontend requirements with Rakesh.
2. Coordinate backend integration with Vijayalakshmi.
3. Verify the AI processing contract.
4. Connect the AI engine to the backend.
5. Test the live camera workflow.
6. Test attendance candidate generation.
7. Test teacher verification.
8. Test attendance finalization.
9. Test offline functionality with Vijayalakshmi.
10. Resolve integration failures.
11. Prepare a complete system demonstration.

COMPLETE WORKFLOW:

Teacher Login
      |
      v
Select Class
      |
      v
Open Authorized Session
      |
      v
Health Check
      |
      v
Camera Capture
      |
      v
Face Detection
      |
      v
Face Quality Assessment
      |
      v
Face Tracking
      |
      v
Open-Set Face Recognition
      |
      v
Attendance Decision Engine
      |
      v
Backend Reconciliation
      |
      v
Teacher Verification
      |
      v
Attendance Finalization
      |
      v
Local Storage / Synchronization

EXPECTED DELIVERABLE:

A complete working software demonstration using a laptop webcam or authorized recorded classroom video.


==================================================
4. DEVELOPMENT PRIORITY
==================================================

Implement the following in order.

P0 — CORE REQUIREMENTS

1. System architecture.
2. Camera input.
3. Face detection.
4. Face quality checking.
5. Face registration and template interface.
6. Face recognition.
7. UNKNOWN detection.
8. Face tracking.
9. Attendance decision engine.
10. Backend integration.

P1 — RELIABILITY AND SECURITY

11. Multi-frame evidence aggregation.
12. Duplicate candidate prevention.
13. AI performance evaluation.
14. Privacy implementation.
15. Error handling.
16. Session validation integration.
17. Integration testing.

P2 — FINAL IMPROVEMENTS

18. Model optimization.
19. Processing speed improvements.
20. Better camera fault handling.
21. Detailed performance reporting.
22. Hardware-readiness documentation.


==================================================
5. TEAM COORDINATION
==================================================

WITH RAKESH — FRONTEND:

You must provide:

- AI processing status requirements.
- Face detection result structure.
- Recognition result structure.
- Attendance candidate status definitions.
- Confidence and reason-code information.
- Live processing state definitions.
- Error and failure states.

Rakesh will handle the presentation of these results in the website.

You must not create or independently modify his React pages.

WITH VIJAYALAKSHMI — BACKEND:

You must coordinate:

- Student face-template registration interface.
- Enrolled template retrieval interface.
- Capture session context.
- AI pipeline input and output.
- Attendance candidate API.
- AI error handling.
- Attendance decision data.
- Offline processing integration.
- Security and privacy boundaries.

Vijayalakshmi owns database persistence and attendance records.

You must not create a separate database implementation.

SHARED RESPONSIBILITY:

- System architecture.
- API contracts.
- Integration testing.
- End-to-end testing.
- Final project documentation.


==================================================
6. GIT AND AI AGENT WORKING RULES
==================================================

Your AI development agent must:

1. Read MANAGE.md before coding.
2. Work primarily inside ai_engine/.
3. Inspect existing files before creating new files.
4. Preserve existing working implementations.
5. Avoid unnecessary dependencies.
6. Never modify Rakesh's frontend without approval.
7. Never modify Vijayalakshmi's backend without approval.
8. Coordinate all shared API changes.
9. Write tests for new AI functionality.
10. Document model selection and licensing.
11. Never put real student data or face images in Git.
12. Report changed files and test results.

RECOMMENDED BRANCH:

feature/paul-ai-engine

For individual features, use additional branches when needed.

Every shared change must be reviewed and coordinated.


==================================================
7. FINAL DELIVERABLES FOR PAUL
==================================================

At the end of Phase 1, you must deliver:

[ ] System architecture documentation.

[ ] Complete AI engine folder.

[ ] Camera input module.

[ ] Multiple face detection module.

[ ] Face quality assessment module.

[ ] Face recognition module.

[ ] Open-set UNKNOWN detection.

[ ] Multi-frame face tracking.

[ ] Attendance decision engine.

[ ] Duplicate candidate prevention.

[ ] Structured AI result interface.

[ ] Backend-AI integration.

[ ] AI privacy implementation.

[ ] Model selection and evaluation report.

[ ] Face detection test results.

[ ] Face recognition test results.

[ ] Tracking test results.

[ ] Performance evaluation report.

[ ] Integration testing report.

[ ] Complete webcam demonstration.

[ ] Phase 2 hardware integration preparation.


==================================================
8. DEFINITION OF DONE
==================================================

Your work is considered complete when:

1. The AI engine can receive webcam or authorized video input.
2. It can detect multiple faces.
3. It can reject poor-quality observations.
4. It can compare faces with registered student templates.
5. It can return UNKNOWN when no match is sufficiently reliable.
6. It can track faces across multiple frames.
7. It can prevent duplicate attendance candidates.
8. It can generate structured attendance suggestions.
9. It can communicate with the FastAPI backend.
10. Raw classroom frames are not permanently stored.
11. All important AI modules have relevant tests.
12. The complete attendance workflow works with the frontend and backend.
13. Technical limitations and measured results are documented.

The system must never mark a student absent automatically because their face was not detected.


==================================================
9. FINAL INSTRUCTION TO YOUR AI CODING AGENT
==================================================

You are working as Paul's AI Engineering Agent for RIT-Sync Vision.

Your responsibility is to develop the AI engine and support the system architecture and integration.

Read MANAGE.md before starting.

Follow the defined folder structure and ownership rules.

Do not modify another developer's files without coordination.

Do not build unnecessary microservices.

Do not create a separate database.

Do not implement frontend pages.

Do not force face recognition results.

Do not automatically finalize attendance.

Do not store raw classroom frames.

Work in small, testable modules.

For every task:
- Inspect existing implementation.
- Understand dependencies.
- Implement the required functionality.
- Add relevant tests.
- Update documentation.
- Report changed files.
- Report actual test results.
- Mention limitations and pending integration work.

PRIORITY:

Correctness → Reliability → Privacy → Integration → Performance → Optimization.

FINAL PROJECT PRINCIPLE:

AI proposes attendance.
The teacher verifies attendance.
The backend stores attendance.

NOT OBSERVED ≠ ABSENT.

END OF PAUL'S DEVELOPMENT PLAN.