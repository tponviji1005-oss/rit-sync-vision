"""
RIT-Sync Vision - End-to-End AI Pipeline Demonstration
Author: Paul Bryton Raj (AI & System Lead)

Demonstrates the Phase 1 AI attendance workflow:
1. Health check (camera, detector, encoder, storage, clock)
2. Enrollment of student templates from images
3. Bounded, authorized capture session
4. Detection, quality gate, tracking, open-set recognition
5. Structured candidates (PRESENT_CANDIDATE / NEEDS_REVIEW / NOT_OBSERVED - never ABSENT)

Usage:
    # Simulated classroom (sample image, no camera needed)
    python scripts/demo_ai_pipeline.py

    # Live webcam demo: enroll yourself from a photo, then sit in front of the webcam
    python scripts/demo_ai_pipeline.py --source 0 --enroll me.jpg --name "Your Name" --duration 30

    # Recorded (authorized) classroom video
    python scripts/demo_ai_pipeline.py --source clip.mp4 --enroll a.jpg --name "Student A"

Enrollment images are read from disk and only their embeddings are kept in memory.
Install the SFace model first for meaningful recognition: python scripts/download_models.py
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Generator, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from shared.constants import AttendanceCandidateState
from shared.schemas import EnrolledTemplate, SessionContext
from ai_engine.camera_input import CameraInputAdapter
from ai_engine.enrollment import FaceEnroller
from ai_engine.pipeline import AIEnginePipeline


class ClassroomSimulationCameraAdapter(CameraInputAdapter):
    """Replays one sample image as a classroom feed (media time, no real-time waiting)."""

    def __init__(self, frame_bgr: np.ndarray, fps_target: int = 10):
        super().__init__(source="synthetic", fps_target=fps_target)
        self.frame = frame_bgr

    def stream_frames(self, duration_seconds: float = 30) -> Generator[Tuple[int, float, np.ndarray], None, None]:
        self.start_capture()
        try:
            for idx in range(int(duration_seconds * self.fps_target)):
                if self._stop_event.is_set():
                    self.stopped_by_teacher = True
                    break
                yield idx, time.time(), self.frame.copy()
        finally:
            self.stop_capture()


def sample_frame() -> np.ndarray:
    from skimage import data  # dev-only dependency

    return cv2.resize(cv2.cvtColor(data.astronaut(), cv2.COLOR_RGB2BGR), (640, 480))


def parse_args():
    ap = argparse.ArgumentParser(description="RIT-Sync Vision AI pipeline demo")
    ap.add_argument("--source", default="sim", help="'sim', webcam index (e.g. 0) or video file path")
    ap.add_argument("--enroll", action="append", default=[], help="Enrollment image path (repeatable)")
    ap.add_argument("--name", action="append", default=[], help="Name for each --enroll image")
    ap.add_argument("--duration", type=int, default=30, help="Capture window, 30-120 s")
    return ap.parse_args()


def main():
    args = parse_args()
    print("=" * 78)
    print("  RIT-SYNC VISION - END-TO-END AI ATTENDANCE PIPELINE DEMO")
    print("=" * 78)

    pipeline = AIEnginePipeline(min_evidence_frames=3)
    enroller = FaceEnroller(detector=pipeline.detector, encoder=pipeline.encoder)

    if args.source == "sim":
        frame = sample_frame()
        camera = ClassroomSimulationCameraAdapter(frame)
        enroll_sets = [("STU_101", "Student A (in view)", [frame])]
    else:
        source = int(args.source) if args.source.isdigit() else args.source
        camera = CameraInputAdapter(source=source)
        if not args.enroll:
            sys.exit("Provide at least one --enroll image for a live/video demo.")
        enroll_sets = []
        for i, path in enumerate(args.enroll):
            img = cv2.imread(path)
            if img is None:
                sys.exit(f"Cannot read enrollment image: {path}")
            name = args.name[i] if i < len(args.name) else f"Student {i + 1}"
            enroll_sets.append((f"STU_{101 + i}", name, [img]))

    health = pipeline.check_health(camera_adapter=camera)
    print(f"\n[1] Health: {health.overall_status}")
    for k, v in health.details.items():
        print(f"    - {k}: {v}")

    print("\n[2] Enrollment")
    templates: List[EnrolledTemplate] = []
    for sid, name, imgs in enroll_sets:
        res = enroller.enroll_images(sid, name, imgs)
        print(f"    {'OK ' if res.success else 'FAIL'} {sid} {name}: {res.message} "
              f"{[r.value for r in res.reason_codes]}")
        if res.template:
            templates.append(res.template)

    roster = [sid for sid, _, _ in enroll_sets] + ["STU_999"]
    names = {sid: name for sid, name, _ in enroll_sets}
    names["STU_999"] = "Student Not In View"

    ctx = SessionContext(
        session_id="SESS_DEMO",
        class_id="CSE-F",
        subject_id="CS301",
        teacher_id="TCH_DEMO",
        permit_id="PERMIT_DEMO",
        duration_seconds=max(30, min(120, args.duration)),
    )
    print(f"\n[3] Capture window: {ctx.duration_seconds}s on source '{args.source}'")

    def progress(p):
        if "frames_processed" in p:
            print(f"    ... {p['frames_processed']} frames, {p['total_tracks']} tracks", end="\r")

    result = pipeline.process_session(ctx, camera, templates, roster, names, on_progress=progress)

    print(f"\n\n[4] Status: {result.status.value}  faults={[r.value for r in result.fault_reasons]}")
    print(f"    Frames: {result.total_frames_processed}  Tracks: {result.total_tracks_detected}  "
          f"Time: {result.processing_time_ms:.0f} ms")
    if result.total_frames_processed:
        print(f"    ~{result.processing_time_ms / result.total_frames_processed:.1f} ms/frame (end-to-end)")
    print(f"    Models: {result.model_version}")

    print("\n[5] Candidates for teacher review")
    print("-" * 78)
    for c in result.candidates:
        print(f"{c.student_id:<9} {c.student_name[:28]:<28} {c.candidate_state.value:<18} "
              f"ev={c.evidence_count:<4} conf={c.confidence:.2f} {[r.value for r in c.reason_codes]}")
    print("-" * 78)

    assert all(c.candidate_state != "ABSENT" for c in result.candidates)
    not_seen = next(c for c in result.candidates if c.student_id == "STU_999")
    assert not_seen.candidate_state == AttendanceCandidateState.NOT_OBSERVED
    print("NOT_OBSERVED != ABSENT enforced. The teacher finalizes every record.\n")


if __name__ == "__main__":
    main()
