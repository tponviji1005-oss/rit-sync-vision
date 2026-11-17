# RIT-Sync Vision: Phase 1 AI Integration Report

**Author:** Paul Bryton Raj (AI & System Lead)
**Status:** AI engine feature-complete for software Phase 1. Evaluation and full-system integration are still pending.
**Date:** 2026-11-18

---

## 1. Summary

The AI engine implements the full observation pipeline from `ai_engine/plan.md`:

authorization guard → camera → detection → quality gate → tracking → open-set recognition → reconciliation → candidates.

The 2026-11-17 version of this report marked every item COMPLETE. A review against the plan then found:

- A crash: any face track with zero usable frames made the whole session `FAILED`.
- A placeholder recognition encoder.
- A missing detector fallback.
- Camera faults reported as success.
- No permit checks.

These have been fixed (see §3). Measured recognition accuracy is still outstanding.

## 2. Deliverable status (plan §7)

| Deliverable | Status | Evidence |
|---|---|---|
| System architecture documentation | Done | `docs/SYSTEM_ARCHITECTURE.md`, `docs/AI_WORKFLOW.md` |
| Camera input module | Done | `ai_engine/camera_input.py`: webcam/video/synthetic, faults, teacher stop |
| Multiple face detection | Done | YuNet, with Haar/LBP fallback |
| Face quality assessment | Done | `detection/face_quality.py`, `quality_check/*` |
| Face recognition | Done, needs model download | SFace when installed; `gradient_v1` dev fallback |
| Open-set UNKNOWN detection | Done | threshold + margin + model-version check |
| Multi-frame tracking | Done | IoU tracklets, frame spans, identity-switch check |
| Attendance decision engine | Done | NOT_OBSERVED ≠ ABSENT, enforced by tests |
| Duplicate candidate prevention | Done | merges fragmented tracks; flags simultaneous ones as conflicts |
| Structured AI result interface | Done | `AIProcessingResult` now carries `fault_reasons`, `model_version`, `config` |
| Backend-AI integration | Partial | `/api/v1/ai/health`, `/process-session`. Enrollment, progress and stop are not yet exposed over HTTP (needs backend coordination) |
| AI privacy implementation | Done for AI side | frame release, no crop retention, log/storage audit, template key guard |
| Model selection & evaluation report | Partial | `docs/AI_MODEL_EVALUATION.md`; accuracy not measured |
| Detection / recognition / tracking test results | Partial | 47 automated tests; no real-data metrics yet |
| Performance evaluation report | Partial | timing measured with dev encoder only |
| Integration testing report | Partial | backend adapter tested; frontend and DB integration not started |
| Webcam demonstration | Ready to run | `python scripts/demo_ai_pipeline.py --source 0 --enroll me.jpg --name "..."` |
| Phase 2 hardware preparation | Done (doc) | `docs/HARDWARE_READINESS.md` |

## 3. Fixes made in the 2026-11-18 review

1. `Observation.evidence_count` now allows 0, and observations report `total_observations`. A regression test reproduces the old crash.
2. The SFace recognizer is integrated, with landmark alignment. Weights come from `scripts/download_models.py`. Templates carry `model_version`, and mismatched ones are never compared.
3. Detector fallback: Haar on OpenCV 4.x, scikit-image LBP on OpenCV 5. Health reports which detector is active.
4. A camera disconnect or unreadable frame now ends in `FAILED` + `CAMERA_DISCONNECTED`, with every present candidate downgraded to `NEEDS_REVIEW`. Reaching the end of a recorded video counts as normal completion.
5. A teacher stop (`camera_adapter.request_stop()`) ends in `STOPPED` + `CAPTURE_STOPPED_BY_TEACHER`.
6. `SessionGuard`: a missing, invalid or expired permit means the camera is never opened. There is a hook for a backend permit verifier. The capture window is limited to 30–120 s.
7. Health checks are real: detector, encoder, storage writability and clock plausibility.
8. Tracks that never overlap in time are merged as one person. Only simultaneous tracks are flagged `CONFLICTING_IDENTITY`. An identity switch inside one track is also flagged.
9. Privacy:
   - The tracker no longer keeps face crops.
   - Frames are released after each frame.
   - Errors log only the exception type.
   - The dev template key raises an error outside development.
   - `PrivacyAuditor` scans `logs/` and detects embedding or image dumps in log files.
10. A progress callback reports state transitions and counts for a live status view.
11. Added `ai_engine/enrollment.py` (image → template), `scripts/evaluate_ai.py` and `ai_engine/requirements.txt`.

## 4. Contract changes to coordinate (shared/)

The following changes affect Vijayalakshmi's backend and Rakesh's frontend:

- `Observation.evidence_count` `ge=0`, plus a new `total_observations`.
- `SessionContext.duration_seconds` now 30–120 (was 1–120), plus a new optional `permit_expires_at`.
- `AIProcessingResult` gains `fault_reasons`, `model_version` and `config`. `status` can now be `STOPPED`.
- New reason codes: `PERMIT_INVALID`, `MODEL_UNAVAILABLE`, `MODEL_VERSION_MISMATCH`, `CAPTURE_STOPPED_BY_TEACHER`.

## 5. Pending work

1. Download SFace, run `scripts/evaluate_ai.py` on a consented dataset, and calibrate the threshold. Update `AI_MODEL_EVALUATION.md` with the measured values.
2. Backend: an enrollment endpoint using `FaceEnroller` plus encrypted storage, a permit verifier, background session execution with progress and a stop endpoint.
3. Frontend: display the states and reason codes defined in `shared/constants`.
4. Live webcam demonstration with the team, and an end-to-end test through the teacher review and finalization flow.
5. A PAD test by attack type (photo, screen replay), per `HARDWARE_READINESS.md` §4.
