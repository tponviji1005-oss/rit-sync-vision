"""
RIT-Sync Vision - AI Evaluation Harness (Phase J)
Author: Paul Bryton Raj (AI & System Lead)

Measures open-set 1:N recognition and pipeline performance on a LOCAL, CONSENTED dataset.
Never commit the dataset or face images (evaluation_data/ is gitignored).

Dataset layout:
    <data>/enrolled/<student_id>/*.jpg    first --enroll-per-id images enroll the student,
                                          the remaining images are genuine probes
    <data>/impostors/<person>/*.jpg       people NOT enrolled; every image is an impostor probe
    <data>/videos/*.mp4                   optional authorized classroom clips (pipeline timing)

Metrics (per probe image, open-set protocol after NIST FRTE 1:N terminology):
    FPIR      impostor probes returned as MATCHED (any identity) / impostor probes
    FNIR      genuine probes not MATCHED to their true identity / genuine probes
    Wrong-ID  genuine probes MATCHED to a different enrolled identity / genuine probes
    Review    probes routed to NEEDS_REVIEW / all probes
    FTA       probes with no usable face (failure to acquire) - reported separately
Plus a threshold sweep (FPIR/FNIR vs similarity threshold) to calibrate the open-set threshold,
detection/encoding latency per image and, for videos, end-to-end ms/frame.

Usage:
    python scripts/evaluate_ai.py --data evaluation_data --out reports/evaluation
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from shared.constants import MatchState
from shared.schemas import EnrolledTemplate, SessionContext
from ai_engine.camera_input import CameraInputAdapter
from ai_engine.enrollment import FaceEnroller
from ai_engine.pipeline import AIEnginePipeline
from ai_engine.recognition.unknown_detector import UnknownDetector

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}


def list_images(d: Path) -> List[Path]:
    return sorted(p for p in d.iterdir() if p.suffix.lower() in IMAGE_EXTS)


def best_face_embedding(pipeline: AIEnginePipeline, img: np.ndarray) -> Tuple[Optional[List[float]], float]:
    """Largest usable face in the image -> embedding. Returns (embedding|None, elapsed_ms)."""
    t0 = time.perf_counter()
    dets = pipeline.detector.detect_faces(img)
    usable = [d for d in dets if d.quality.is_usable]
    emb = None
    if usable:
        d = max(usable, key=lambda x: x.bbox.width * x.bbox.height)
        emb = pipeline.encoder.encode(d.face_crop, enforce_quality=False,
                                      source_frame=d.source_frame, face_row=d.face_row)
    for d in dets:
        d.release()
    return emb, (time.perf_counter() - t0) * 1000.0


def top2(query: List[float], templates: List[EnrolledTemplate]) -> Tuple[Optional[str], float, float]:
    q = np.asarray(query, dtype=np.float32)
    sims = sorted(
        ((float(np.dot(q, np.asarray(t.embedding, dtype=np.float32))), t.student_id) for t in templates),
        reverse=True,
    )
    best_sim, best_id = sims[0]
    second = sims[1][0] if len(sims) > 1 else -1.0
    return best_id, best_sim, second


def sweep(genuine, impostor, margin: float) -> List[Dict]:
    """genuine: [(true_id, best_id, best, second)], impostor: [(best, second)]"""
    rows = []
    for thr in np.round(np.arange(0.10, 0.96, 0.025), 3):
        fp = sum(1 for b, s in impostor if b >= thr and (b - s) >= margin)
        fn = sum(1 for t, bid, b, s in genuine if not (b >= thr and (b - s) >= margin and bid == t))
        rows.append({
            "threshold": float(thr),
            "FPIR": fp / len(impostor) if impostor else None,
            "FNIR": fn / len(genuine) if genuine else None,
        })
    return rows


def evaluate_images(
    pipeline: AIEnginePipeline, data: Path, enroll_per_id: int
) -> Tuple[Dict, List[EnrolledTemplate]]:
    enroller = FaceEnroller(detector=pipeline.detector, encoder=pipeline.encoder)
    judge = UnknownDetector(pipeline.similarity_threshold, pipeline.margin_threshold)
    mv = pipeline.encoder.model_version

    templates: List[EnrolledTemplate] = []
    genuine_probes: List[Tuple[str, Path]] = []
    enroll_failures = []
    for sdir in sorted(p for p in (data / "enrolled").iterdir() if p.is_dir()):
        imgs = list_images(sdir)
        if len(imgs) <= enroll_per_id:
            continue
        enroll_imgs = [cv2.imread(str(p)) for p in imgs[:enroll_per_id]]
        res = enroller.enroll_images(sdir.name, sdir.name, [i for i in enroll_imgs if i is not None])
        if not res.success:
            enroll_failures.append(sdir.name)
            continue
        templates.append(res.template)
        genuine_probes += [(sdir.name, p) for p in imgs[enroll_per_id:]]

    if not templates:
        raise SystemExit("No identity could be enrolled; check the dataset images.")

    impostor_probes: List[Path] = []
    imp_root = data / "impostors"
    if imp_root.exists():
        for pdir in sorted(p for p in imp_root.iterdir() if p.is_dir()):
            impostor_probes += list_images(pdir)

    counts = {"genuine": 0, "impostor": 0, "fta": 0, "fp": 0, "fn": 0, "wrong_id": 0, "review": 0}
    latencies, sweep_gen, sweep_imp = [], [], []

    for is_genuine, true_id, path in (
        [(True, t, p) for t, p in genuine_probes] + [(False, None, p) for p in impostor_probes]
    ):
        img = cv2.imread(str(path))
        if img is None:
            continue
        emb, ms = best_face_embedding(pipeline, img)
        latencies.append(ms)
        counts["genuine" if is_genuine else "impostor"] += 1
        if emb is None:
            counts["fta"] += 1
            if is_genuine:
                counts["fn"] += 1
            continue

        res = judge.identify(emb, templates, model_version=mv)
        bid, b, s = top2(emb, templates)
        if res.match_state == MatchState.NEEDS_REVIEW:
            counts["review"] += 1
        if is_genuine:
            sweep_gen.append((true_id, bid, b, s))
            if res.match_state == MatchState.MATCHED and res.student_id != true_id:
                counts["wrong_id"] += 1
            if not (res.match_state == MatchState.MATCHED and res.student_id == true_id):
                counts["fn"] += 1
        else:
            sweep_imp.append((b, s))
            if res.match_state == MatchState.MATCHED:
                counts["fp"] += 1

    g, i = counts["genuine"], counts["impostor"]
    return {
        "enrolled_identities": len(templates),
        "enrollment_failures": enroll_failures,
        "genuine_probes": g,
        "impostor_probes": i,
        "FPIR": counts["fp"] / i if i else None,
        "FNIR": counts["fn"] / g if g else None,
        "wrong_id_rate": counts["wrong_id"] / g if g else None,
        "review_rate": counts["review"] / (g + i) if (g + i) else None,
        "failure_to_acquire_rate": counts["fta"] / (g + i) if (g + i) else None,
        "latency_ms_per_image": {
            "mean": float(np.mean(latencies)) if latencies else None,
            "p95": float(np.percentile(latencies, 95)) if latencies else None,
        },
        "threshold_sweep": sweep(sweep_gen, sweep_imp, pipeline.margin_threshold),
        "counts": counts,
    }, templates


def evaluate_videos(pipeline: AIEnginePipeline, data: Path, templates: List[EnrolledTemplate], duration: int) -> List[Dict]:
    out = []
    vdir = data / "videos"
    if not vdir.exists():
        return out
    roster = [t.student_id for t in templates]
    for vid in sorted(p for p in vdir.iterdir() if p.suffix.lower() in VIDEO_EXTS):
        ctx = SessionContext(session_id=f"EVAL_{vid.stem}", class_id="EVAL", subject_id="EVAL",
                             teacher_id="EVAL", permit_id="EVAL", duration_seconds=duration)
        res = pipeline.process_session(ctx, CameraInputAdapter(source=str(vid)), templates, roster)
        states: Dict[str, int] = {}
        for c in res.candidates:
            states[c.candidate_state.value] = states.get(c.candidate_state.value, 0) + 1
        obs_states: Dict[str, int] = {}
        for o in res.observations:
            obs_states[o.match_state.value] = obs_states.get(o.match_state.value, 0) + 1
        out.append({
            "video": vid.name,
            "status": res.status.value,
            "frames": res.total_frames_processed,
            "tracks": res.total_tracks_detected,
            "ms_per_frame": res.processing_time_ms / res.total_frames_processed if res.total_frames_processed else None,
            "total_processing_ms": res.processing_time_ms,
            "candidate_states": states,
            "observation_states": obs_states,
            "usable_track_share": (
                sum(1 for o in res.observations if o.evidence_count > 0) / len(res.observations)
                if res.observations else None
            ),
        })
    return out


def _ms(x):
    return "n/a" if x is None else f"{x:.1f}"


def pct(x):
    return "n/a" if x is None else f"{100 * x:.2f}%"


def to_markdown(report: Dict) -> str:
    im = report["images"]
    lines = [
        "# AI Evaluation Report (generated)",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Models: `{report['model_version']}`",
        f"- Config: `{json.dumps(report['config'])}`",
        "",
        "## Open-set 1:N recognition (images)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Enrolled identities | {im['enrolled_identities']} |",
        f"| Genuine / impostor probes | {im['genuine_probes']} / {im['impostor_probes']} |",
        f"| FPIR | {pct(im['FPIR'])} |",
        f"| FNIR | {pct(im['FNIR'])} |",
        f"| Wrong-ID rate | {pct(im['wrong_id_rate'])} |",
        f"| Review rate | {pct(im['review_rate'])} |",
        f"| Failure to acquire | {pct(im['failure_to_acquire_rate'])} |",
        f"| Latency / image (mean, p95) | {_ms(im['latency_ms_per_image']['mean'])} / {_ms(im['latency_ms_per_image']['p95'])} ms |",
        "",
        "## Threshold sweep (margin fixed)",
        "",
        "| Threshold | FPIR | FNIR |",
        "|---|---|---|",
    ]
    lines += [f"| {r['threshold']:.3f} | {pct(r['FPIR'])} | {pct(r['FNIR'])} |" for r in im["threshold_sweep"]]
    if report["videos"]:
        lines += ["", "## Pipeline on recorded video", "",
                  "| Video | Status | Frames | Tracks | ms/frame | Usable-track share | Candidates |",
                  "|---|---|---|---|---|---|---|"]
        for v in report["videos"]:
            mspf = f"{v['ms_per_frame']:.1f}" if v["ms_per_frame"] else "n/a"
            lines.append(f"| {v['video']} | {v['status']} | {v['frames']} | {v['tracks']} | {mspf} | "
                         f"{pct(v['usable_track_share'])} | {v['candidate_states']} |")
    lines += ["", "Results apply only to this dataset and these conditions. They are not guarantees."]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="RIT-Sync Vision AI evaluation")
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--out", default=Path("reports/evaluation"), type=Path)
    ap.add_argument("--enroll-per-id", type=int, default=2)
    ap.add_argument("--video-duration", type=int, default=30)
    ap.add_argument("--threshold", type=float, default=None, help="Override similarity threshold")
    ap.add_argument("--margin", type=float, default=None, help="Override margin threshold")
    args = ap.parse_args()

    if not (args.data / "enrolled").is_dir():
        print(f"Missing {args.data / 'enrolled'}; see the dataset layout in this script's docstring.")
        return 2

    pipeline = AIEnginePipeline(similarity_threshold=args.threshold, margin_threshold=args.margin)
    if not pipeline.encoder.is_identity_model:
        print("WARNING: SFace not installed; results use the development gradient encoder and are not meaningful.")

    image_report, templates = evaluate_images(pipeline, args.data, args.enroll_per_id)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": pipeline.model_version,
        "config": pipeline.config_snapshot(),
        "images": image_report,
        "videos": evaluate_videos(pipeline, args.data, templates, args.video_duration),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (args.out / f"evaluation_{stamp}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = to_markdown(report)
    (args.out / f"evaluation_{stamp}.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
