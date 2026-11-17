# RIT-Sync Vision: AI Model Evaluation & Performance Metrics

**Author:** Paul Bryton Raj (AI & System Lead)
**Version:** 1.1 (2026-11-18)
**Status:** Harness ready; recognition accuracy **not yet measured** on real, consented data.

---

## 1. Model selection

| Stage | Selected | Alternatives considered | Reason |
|---|---|---|---|
| Detection | OpenCV **YuNet** 2023mar (MIT) | Haar/LBP cascades (kept as fallback), MTCNN, RetinaFace | Multi-face, gives landmarks for alignment, small (~230 KB), runs on CPU through OpenCV with no extra dependency |
| Recognition | OpenCV **SFace** 2021dec (Apache-2.0) | ArcFace/InsightFace (model licence restricts commercial use), FaceNet, dlib | Permissive licence, 128-d, native YuNet alignment, no extra pip dependency |
| Dev baseline | `gradient_v1` | n/a | Deterministic, for unit tests only. Not a recognition model |

Licences are listed in `ai_engine/models/README.md`.

## 2. Metrics framework

Following NIST FRTE 1:N terminology and the ISO/IEC 19795 approach, `scripts/evaluate_ai.py` reports:

1. **FPIR**: share of impostor (unenrolled) probes returned as `MATCHED`.
2. **FNIR**: share of genuine probes that are not `MATCHED` to their true identity.
3. **Wrong-ID rate**: share of genuine probes `MATCHED` to a different enrolled student.
4. **Review rate**: share of probes routed to `NEEDS_REVIEW`.
5. **Failure to acquire**: share of probes with no usable face (quality gate or detector).
6. **Threshold sweep**: FPIR and FNIR across similarity thresholds, used for calibration.
7. **Latency**: detect + encode time per image, and end-to-end ms/frame on recorded video.
8. **Usable-track share** per video, a proxy for seat-zone coverage. The real per-seat measurement needs the Phase 2 camera geometry work.

Run:

```bash
python scripts/download_models.py           # SFace weights
python scripts/evaluate_ai.py --data evaluation_data --out reports/evaluation
```

The dataset layout is documented in the script. `evaluation_data/` and `reports/evaluation/` are gitignored. **Never commit face images.**

## 3. Measured results so far

Hardware: development laptop CPU. Input: 640×480 sample image (scikit-image "astronaut", public domain). Encoder: `gradient_v1`.

| Measurement | Result | Notes |
|---|---|---|
| End-to-end pipeline, simulated feed | **~19 ms/frame** (300 frames, 1 face) | detect + quality + track + encode |
| Pipeline on recorded clip (MJPG .avi) | **~14 ms/frame** (30 frames, 1 face) | media-time window |
| Detect + encode per still image | **~11 ms** mean | 1 face |
| Recognition FPIR / FNIR / wrong-ID | **Not measured** | Needs SFace plus a consented multi-person dataset |
| Seat-zone coverage | **Not measured** | Needs the classroom camera geometry test (Phase 2 / validation B) |

The timing will rise with SFace and with more faces per frame. Re-measure after installing SFace.

## 4. Validation targets (from the PPT, not results)

| Area | Proposed target | Status |
|---|---|---|
| Camera coverage | ≥ 95% usable face tracks per seat zone | Not measured |
| Identity safety | No unreviewed wrong-ID finalization | Enforced by design: AI never finalizes. Ambiguous, conflicting and fault-affected results go to `NEEDS_REVIEW` |
| Roster ready time | 60–120 s | Capture window is 30–120 s. Processing time is measured per run (`processing_time_ms`) |
| Frame privacy | 0 raw frames persisted | Covered by tests (`PrivacyAuditor` on `storage/` and `logs/`) |

## 5. Known limitations

- Recognition accuracy is unknown until the evaluation is run with SFace on consented data.
- The SFace default threshold comes from LFW (frontal, well-lit faces). Classroom images (small, distant, angled faces) will behave differently, so calibrate before any pilot.
- There is no presentation attack detection (PAD). A printed photo or a phone screen can be detected and matched. See `docs/HARDWARE_READINESS.md` §4.
- No demographic-differential analysis has been done yet (NISTIR 8280). Plan it for the shadow test.
