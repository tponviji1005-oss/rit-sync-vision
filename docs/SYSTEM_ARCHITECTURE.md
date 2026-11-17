# RIT-Sync Vision — System Architecture & Cross-Module Contracts

**Document Version:** 1.0  
**Authors:** Paul Bryton Raj (AI & System Lead), Pon Vijayalakshmi (Backend Lead), Rakesh Anand (Frontend Lead)  
**Status:** Approved Working Baseline  

---

## 1. Architectural Model

RIT-Sync Vision is designed as a **modular monolith** in a single monorepo:

```
rit-sync-vision/
├── frontend/       # Rakesh: React + TypeScript + Tailwind CSS UI
├── backend/        # Vijayalakshmi: FastAPI application, SQLite/PostgreSQL, sync queue
├── ai_engine/      # Paul: Python computer vision & recognition engine
├── shared/         # Agreed contracts (constants, schemas)
├── storage/        # Local data (database, encrypted templates, temp files)
└── docs/           # Specifications & evaluation reports
```

### Monolithic Runtime Integration (Phase 1)
```
[React Browser UI] 
       │
       │ HTTP / JSON API (/api/v1/...)
       ▼
[FastAPI Backend]
       ├── Auth, Users, Students, Sessions, Audit, Sync Queue
       ├── Local Database (SQLite)
       └── Calls internal ai_engine via Python API
               │
               ▼
       [AI Engine Package]
               ├── Camera Adapter (Webcam / Video)
               ├── Face Detection & Quality Gate
               ├── Face Tracklets (Multi-Frame)
               ├── Open-Set 1:N Recognition
               └── Attendance Decision Engine
```

---

## 2. Fundamental Operating Principles

1. **Teacher Authority:**  
   The AI proposes attendance candidates; the teacher explicitly confirms and finalizes every attendance record.
2. **`NOT OBSERVED ≠ ABSENT`:**  
   If a student is not observed by the camera, the system marks them as `NOT_OBSERVED`. The system will **never** automatically infer `ABSENT`.
3. **Open-Set Identification:**  
   The camera will see non-registered individuals. The engine supports an explicit `UNKNOWN` state and will never force a nearest-match registered identity.
4. **Privacy by Default:**  
   Raw classroom video frames are processed in-memory and immediately discarded. No raw camera frames are stored on disk, sent over the network, or saved in audit logs.
5. **Multi-Frame Evidence:**  
   Decisions require multi-frame tracking and evidence accumulation; a single momentary frame cannot unilaterally declare identity.
