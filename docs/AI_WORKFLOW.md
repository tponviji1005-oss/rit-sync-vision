# RIT-Sync Vision — AI Engine Workflow Specification

**Author:** Paul Bryton Raj (AI & System Lead)  
**Version:** 1.0  

---

## 1. High-Level AI Pipeline Flow

The AI Engine processes input during a bounded capture window (30–120 seconds):

```mermaid
flowchart TD
    A["Camera Input (Webcam / Video)"] --> B["Face Detection (OpenCV / Haar / DNN)"]
    B --> C{"Quality Gate Check"}
    C -- "Fails Blur / Size / Lighting" --> D["Mark INSUFFICIENT_QUALITY + Reason Code"]
    C -- "Passes Quality" --> E["Face Tracklet Association (IoU & Temporal Matching)"]
    E --> F["Face Feature Extraction (Embedding)"]
    F --> G["Open-Set 1:N Recognition (Cosine Similarity)"]
    G --> H{"Threshold & Margin Check"}
    H -- "Sim < 0.65" --> I["UNKNOWN (Unenrolled Person)"]
    H -- "Best vs 2nd < 0.10" --> J["NEEDS_REVIEW (Ambiguous Match)"]
    H -- "Sim >= 0.65 & Margin >= 0.10" --> K["MATCHED to Student ID"]
    K --> L["Multi-Frame Evidence Accumulator"]
    I --> L
    J --> L
    D --> L
    L --> M["Attendance Decision Engine & Duplicate Reconciler"]
    M --> N["Generate Structured Output (Candidates & Observations)"]
```

---

## 2. Decision Logic & Thresholds

| Parameter | Default Value | Purpose |
|---|---|---|
| `MIN_FACE_SIZE_PIXELS` | 48 pixels | Rejects distant/small faces that cannot be reliably recognized |
| `BLUR_THRESHOLD` | 80.0 | Minimum Laplacian variance to prevent motion blur misidentifications |
| `BRIGHTNESS_MIN` | 40.0 | Minimum luminance (prevents underexposed faces) |
| `BRIGHTNESS_MAX` | 225.0 | Maximum luminance (prevents blown-out/overexposed faces) |
| `COSINE_SIM_THRESHOLD` | 0.65 | Minimum similarity required to match an enrolled student |
| `SECOND_BEST_MARGIN` | 0.10 | Distance between #1 and #2 match; prevents ambiguous assignment |
| `MIN_EVIDENCE_FRAMES` | 3 frames | Minimum number of valid frames needed for `PRESENT_CANDIDATE` |

---

## 3. Candidate Outcome Matrix

| Observation Criteria | AI Candidate State | Reason Codes |
|---|---|---|
| $\ge 3$ frames, Sim $\ge 0.65$, Margin $\ge 0.10$ | `PRESENT_CANDIDATE` | `[]` |
| $\ge 1$ frame, Sim $\ge 0.65$, but $< 3$ frames | `NEEDS_REVIEW` | `["INSUFFICIENT_EVIDENCE"]` |
| Sim $\ge 0.65$ but Margin $< 0.10$ | `NEEDS_REVIEW` | `["AMBIGUOUS_MATCH"]` |
| Multiple tracks match same student | `NEEDS_REVIEW` | `["CONFLICTING_IDENTITY", "DUPLICATE_CANDIDATE"]` |
| Low similarity to all enrolled templates | `UNKNOWN` (Track) | `["LOW_MATCH_CONFIDENCE"]` |
| Poor quality / blur / lighting | Unusable Track | `["IMAGE_BLUR"]`, `["FACE_TOO_SMALL"]`, etc. |
| Student on class roster never observed | `NOT_OBSERVED` | `["NOT_OBSERVED"]` (Never `ABSENT`) |
