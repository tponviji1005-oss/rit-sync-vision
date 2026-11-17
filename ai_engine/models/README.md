# AI Models Directory

**Owner:** Paul Bryton Raj (AI & System Lead)

This directory stores model weights and configuration files for face detection and recognition.

---

## 1. Models Baseline

### `haarcascade_frontalface_default.xml`
- **Purpose:** Multi-face bounding box detection and localization.
- **Source:** OpenCV official model repository (Apache 2.0 License).
- **Format:** OpenCV XML Cascade Classifier.
- **Parameters:** Default scale factor 1.1, minimum neighbors 5, minimum face size 48x48.

### Embeddings & Recognition Models
- **Phase 1 Software Baseline:** 128-dimensional L2-normalized gradient/spatial feature encoder (OpenCV/NumPy based) for high-speed deterministic embedding without requiring multi-gigabyte untracked weights.
- **Phase 2 Edge AI Integration:** ONNX Runtime models (e.g., MobileFaceNet / ArcFace ONNX) optimized for Edge compute devices.
