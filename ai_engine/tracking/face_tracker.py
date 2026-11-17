"""
RIT-Sync Vision - Multi-Frame Face Tracker
Author: Paul Bryton Raj (AI & System Lead)

Associates face bounding boxes across consecutive frames using Intersection-over-Union (IoU)
and tracking state machine. Assigns distinct track IDs (e.g. TRK_001).
A track ID is distinct from a student identity.
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from shared.schemas import BoundingBox, FaceQualityResult
from ai_engine.detection.face_detector import DetectionResult


def calculate_iou(boxA: BoundingBox, boxB: BoundingBox) -> float:
    """Computes Intersection-over-Union between two BoundingBox objects."""
    xA = max(boxA.x, boxB.x)
    yA = max(boxA.y, boxB.y)
    xB = min(boxA.x + boxA.width, boxB.x + boxB.width)
    yB = min(boxA.y + boxA.height, boxB.y + boxB.height)

    inter_width = max(0, xB - xA)
    inter_height = max(0, yB - yA)
    inter_area = inter_width * inter_height

    boxA_area = boxA.width * boxA.height
    boxB_area = boxB.width * boxB.height

    union_area = float(boxA_area + boxB_area - inter_area)
    if union_area <= 0:
        return 0.0

    return inter_area / union_area


class ActiveTrack:
    """Tracker state for one visible face. Holds geometry and quality only - never raw face pixels."""

    def __init__(self, track_id: str, initial_bbox: BoundingBox, start_frame: int):
        self.track_id = track_id
        self.last_bbox = initial_bbox
        self.first_frame = start_frame
        self.last_frame = start_frame
        self.total_observations = 1
        self.missed_frames = 0
        self.qualities: List[FaceQualityResult] = []


class FaceTracker:
    """
    Multi-frame temporal tracker matching detections to active tracklets.
    """

    def __init__(self, iou_threshold: float = 0.35, max_missed_frames: int = 5):
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self._next_id = 1
        self.active_tracks: Dict[str, ActiveTrack] = {}

    def _generate_track_id(self) -> str:
        tid = f"TRK_{self._next_id:04d}"
        self._next_id += 1
        return tid

    def update(
        self, frame_index: int, detections: List[DetectionResult]
    ) -> List[Tuple[str, DetectionResult]]:
        """
        Updates tracks with new detections from the current frame.
        :return: List of (track_id, detection_result) for all matched/created tracks in this frame.
        """
        matched_results: List[Tuple[str, DetectionResult]] = []

        if not self.active_tracks and not detections:
            return []

        active_track_ids = list(self.active_tracks.keys())
        unmatched_detections = list(range(len(detections)))
        matched_track_ids = set()

        if active_track_ids and detections:
            # Build IoU cost matrix
            iou_matrix = np.zeros((len(active_track_ids), len(detections)), dtype=np.float32)
            for r, tid in enumerate(active_track_ids):
                for c, det in enumerate(detections):
                    iou_matrix[r, c] = calculate_iou(self.active_tracks[tid].last_bbox, det.bbox)

            # Greedy bipartite matching
            while True:
                max_val = np.max(iou_matrix) if iou_matrix.size > 0 else 0
                if max_val < self.iou_threshold:
                    break

                r, c = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                tid = active_track_ids[r]
                det = detections[c]

                # Update matched track
                track = self.active_tracks[tid]
                track.last_bbox = det.bbox
                track.last_frame = frame_index
                track.total_observations += 1
                track.missed_frames = 0
                track.qualities.append(det.quality)

                matched_track_ids.add(tid)
                if c in unmatched_detections:
                    unmatched_detections.remove(c)

                matched_results.append((tid, det))

                # Zero out row and column
                iou_matrix[r, :] = -1.0
                iou_matrix[:, c] = -1.0

        # Handle unmatched active tracks (increment missed_frames)
        to_delete = []
        for tid, track in self.active_tracks.items():
            if tid not in matched_track_ids:
                track.missed_frames += 1
                if track.missed_frames > self.max_missed_frames:
                    to_delete.append(tid)

        for tid in to_delete:
            del self.active_tracks[tid]

        # Initialize new tracks for unmatched detections
        for c in unmatched_detections:
            det = detections[c]
            new_tid = self._generate_track_id()
            track = ActiveTrack(track_id=new_tid, initial_bbox=det.bbox, start_frame=frame_index)
            track.qualities.append(det.quality)
            self.active_tracks[new_tid] = track
            matched_results.append((new_tid, det))

        return matched_results

    def reset(self):
        """Clears all tracking memory at the end of a session."""
        self.active_tracks.clear()
        self._next_id = 1
