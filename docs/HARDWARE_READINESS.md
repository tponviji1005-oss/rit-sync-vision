# RIT-Sync Vision: Phase 2 Hardware Readiness & Security Test Plan

**Author:** Paul Bryton Raj (AI & System Lead)
**Version:** 1.0 (2026-11-18)

This document prepares the move from the Phase 1 laptop webcam to a dedicated classroom device (PRD §7.2, §19). Nothing here selects hardware. Selection follows the measurements below.

---

## 1. Camera replacement path

The pipeline only depends on `CameraInputAdapter.stream_frames()`, `fault`, `stopped_by_teacher` and `request_stop()`. A classroom camera is integrated by subclassing:

```python
class ClassroomCameraAdapter(CameraInputAdapter):
    def start_capture(self) -> bool: ...    # open RTSP/CSI/USB device, set fault on failure
    def _read_frame(self): ...              # return (ok, frame_bgr)
    def stop_capture(self): ...             # release device, switch capture LED off
```

Requirements for the adapter:

- Set `self.fault = ReasonCode.CAMERA_DISCONNECTED` on any read failure. Never end silently.
- Drive the physical capture indicator (FR-006/FR-103) from `start_capture` and `stop_capture`.
- Keep frames in memory only. Do no recording or buffering to disk.
- Report its resolution and status in `check_health()`.

## 2. Camera geometry checklist (validation stages A/B)

- Measure the room: rows, seat positions, camera mounting height and angle.
- For each seat zone, record the face height in pixels at the chosen resolution and lens. The quality gate rejects faces under 48 px, so aim for 80 px or more at the back row.
- Run `scripts/evaluate_ai.py --data <zone clips>` per zone and report the **usable-track share** per zone. The target is 95% or more.
- Record occlusion and the lighting variation across the day.
- Treat a zone below target as a documented limitation with a manual fallback. It is never grounds for inferring absence.

## 3. Edge compute benchmark checklist

For each candidate device, using the same recorded clips:

| Measure | How |
|---|---|
| Model load time | time `AIEnginePipeline()` construction |
| ms/frame, faces/frame 1, 10, 30 | `evaluate_ai.py` video section |
| Total processing time for a 30 s and a 120 s window | `processing_time_ms` |
| Peak memory | OS tools during a 120 s session |
| Thermal and power | sustained 10-session run |
| Offline queue reliability | owned by the backend; run jointly with Vijayalakshmi |

## 4. Presentation attack (PAD) test plan

Following the ISO/IEC 30107-3 approach, report results per attack type and never as a blanket claim. The current software has **no PAD**. It will match a sufficiently good printed photo or screen replay of an enrolled student.

| Attack | Procedure | Expected today | Metric |
|---|---|---|---|
| Printed photo (A4, colour) | hold in front of camera for the window | likely `PRESENT_CANDIDATE` | APCER per attack type |
| Phone/tablet screen photo | same | likely matched | APCER |
| Video replay on screen | play recorded clip | likely matched | APCER |
| Poor-quality input | blur, dark, far | `INSUFFICIENT_QUALITY` / `NOT_OBSERVED` | rejection rate |
| Tampered metadata | altered permit/session fields | `PERMIT_INVALID` / `PERMIT_EXPIRED` (needs backend verifier) | rejection rate |
| Unauthorized camera access | start session without permit | camera never opened | pass/fail |
| Unauthorized template access | read stored templates without key | AES-GCM ciphertext only | pass/fail |

Mitigations to evaluate in Phase 2:

- Multi-frame liveness cues (blink, head motion across a track).
- IR or depth sensing on the classroom device.
- Teacher review of `PRESENT_CANDIDATE` lists, which remains the final control.

## 5. Security limitations (current)

- A signed permit proves authorization, not genuine live capture or physical presence.
- The development template key is public. Production must set `TEMPLATE_ENCRYPTION_KEY` (enforced when `RIT_ENV` is not development) and should use a hardware key store (TPM) in Phase 2.
- Clock checks on the AI side only catch an obviously wrong clock. Rollback protection with counters and permit expiry belongs to the backend and device design.
- Embeddings are biometric data, even though raw frames are never stored. Protect and revoke them like templates.
