# AI Models Directory

**Owner:** Paul Bryton Raj (AI & System Lead)

Model weights used by the AI engine. Large weights are not committed. Fetch them with:

```bash
python scripts/download_models.py
```

The script verifies a SHA-256 checksum for each file.

| File | Role | Source / licence | In Git? |
|---|---|---|---|
| `face_detection_yunet_2023mar.onnx` | Primary multi-face detector (bbox + 5 landmarks + score) | OpenCV Zoo, MIT | Yes (~230 KB) |
| `haarcascade_frontalface_default.xml` | Detector fallback on OpenCV 4.x (`cv2.CascadeClassifier`) | OpenCV, Intel licence (BSD-style) | Yes |
| `face_recognition_sface_2021dec.onnx` | Face recognition, 128-d embeddings (`cv2.FaceRecognizerSF`) | OpenCV Zoo, Apache-2.0 | **No**: download script, gitignored |

## Selection order at runtime

**Detector** (`detection/face_detector.py`):
1. YuNet.
2. Haar cascade (OpenCV 4.x only).
3. scikit-image LBP frontal cascade, used if OpenCV 5 has no `CascadeClassifier`.

The active backend appears in `health.details["detector"]` and in `AIProcessingResult.model_version`. The fallbacks give no landmarks, so faces are not aligned and recognition quality drops.

**Encoder** (`recognition/face_encoder.py`):
1. SFace, when its model file is present. Faces are aligned using YuNet landmarks.
2. `gradient_v1`: a hand-made gradient histogram, for development and tests only. It is **not** a face-recognition model, and no accuracy should ever be reported with it. The health check shows an `encoder_warning` whenever it is active.

## Versioning rules

- Every `EnrolledTemplate.model_version` must equal the encoder's `model_version` (`sface_2021dec` or `gradient_v1`).
- Templates from another model are never compared. The session reports `MODEL_VERSION_MISMATCH`, and students must be re-enrolled after a model change.

## Default open-set thresholds (must be re-calibrated)

| Encoder | Similarity threshold | Margin (best − 2nd) | Origin |
|---|---|---|---|
| `sface_2021dec` | 0.363 | 0.08 | OpenCV Zoo 1:1 cosine threshold (LFW); margin is a starting guess |
| `gradient_v1` | 0.65 | 0.10 | Arbitrary; only for synthetic tests |

Calibrate the thresholds with `scripts/evaluate_ai.py` on consented project data. Pick the threshold whose FPIR meets the agreed target, and record the result in `docs/AI_MODEL_EVALUATION.md`. A similarity score is **not** a probability that the identity is correct.
