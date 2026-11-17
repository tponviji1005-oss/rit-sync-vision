# RIT-Sync Vision — AI Model Evaluation & Performance Metrics

**Author:** Paul Bryton Raj (AI & System Lead)  
**Version:** 1.0  

---

## 1. Metrics Framework

Per NIST FRTE and ISO/IEC 19795 standards, evaluation focuses on:

1. **False Positive Identification Rate (FPIR):**  
   Rate at which an unenrolled/unknown person is incorrectly matched to an enrolled student.
2. **False Negative Identification Rate (FNIR):**  
   Rate at which an enrolled student is observed under usable conditions but fails to be identified.
3. **Wrong-ID Rate:**  
   Rate at which enrolled student $A$ is incorrectly identified as enrolled student $B$.
4. **Teacher Review Rate:**  
   Percentage of roster observations routed to the teacher as `NEEDS_REVIEW`.
5. **Frame Processing Latency:**  
   Time taken per frame for detection, quality check, tracking, and feature extraction.

---

## 2. Target vs. Observed Benchmark Gates

| Area | Proposed Target | Phase 1 Software Benchmark Goal |
|---|---|---|
| Camera Coverage | $\ge 95\%$ usable face tracks | Measured via synthetic/webcam seat simulations |
| Wrong-ID Finalization | 0 unreviewed wrong IDs | Zero tolerance: ambiguous matches forced to `NEEDS_REVIEW` |
| Roster Prep Time | $60–120$ seconds | $< 100\text{ ms}$ per frame processing time |
| Offline / Frame Privacy | 0 raw frames stored on disk | Tested via file-system inspection assertions |
