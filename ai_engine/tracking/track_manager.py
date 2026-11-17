"""
RIT-Sync Vision - Track Manager
Author: Paul Bryton Raj (AI & System Lead)

Consolidates multi-frame evidence per tracklet:
- Tracks valid observations, quality distribution, and embeddings across frames.
- Records the frame span of each track (used to tell track fragmentation from real conflicts).
- Computes the mean embedding representation for recognition.
- Holds no raw images; all evidence is disposed of at session end.
"""

from typing import Dict, List, Optional
import numpy as np
from shared.schemas import BoundingBox, FaceQualityResult
from shared.constants import ReasonCode


class TrackEvidence:
    """Consolidated evidence collected for a single track across the capture window."""

    def __init__(self, track_id: str):
        self.track_id = track_id
        self.observations_count = 0
        self.usable_observations_count = 0
        self.embeddings: List[List[float]] = []
        self.quality_scores: List[float] = []
        self.accumulated_reasons: List[ReasonCode] = []
        self.last_bbox: Optional[BoundingBox] = None
        self.first_frame: Optional[int] = None
        self.last_frame: Optional[int] = None

    def add_observation(
        self,
        quality: FaceQualityResult,
        embedding: Optional[List[float]],
        bbox: BoundingBox,
        frame_index: Optional[int] = None,
    ):
        self.observations_count += 1
        self.quality_scores.append(quality.quality_score)
        self.last_bbox = bbox

        if frame_index is not None:
            if self.first_frame is None or frame_index < self.first_frame:
                self.first_frame = frame_index
            if self.last_frame is None or frame_index > self.last_frame:
                self.last_frame = frame_index

        if quality.is_usable and embedding is not None:
            self.usable_observations_count += 1
            self.embeddings.append(embedding)
        else:
            for r in quality.reason_codes:
                if r not in self.accumulated_reasons:
                    self.accumulated_reasons.append(r)

    def overlaps(self, other: "TrackEvidence") -> bool:
        """True if both tracks were visible in at least one common frame range.
        Tracks without frame information are conservatively treated as overlapping."""
        if None in (self.first_frame, self.last_frame, other.first_frame, other.last_frame):
            return True
        return self.first_frame <= other.last_frame and other.first_frame <= self.last_frame

    def get_representative_embedding(self) -> Optional[List[float]]:
        """
        Computes the L2-normalized mean embedding across all usable frames for this track.
        Multi-frame averaging reduces per-frame noise and pose variance.
        """
        if not self.embeddings:
            return None

        arr = np.array(self.embeddings, dtype=np.float32)
        mean_vec = np.mean(arr, axis=0)
        norm = np.linalg.norm(mean_vec)
        if norm > 0:
            mean_vec = mean_vec / norm
        return [round(float(x), 6) for x in mean_vec]


class TrackManager:
    """
    Manages session-wide track evidence accumulation and lifecycle.
    """

    def __init__(self):
        self.tracks: Dict[str, TrackEvidence] = {}

    def get_or_create(self, track_id: str) -> TrackEvidence:
        if track_id not in self.tracks:
            self.tracks[track_id] = TrackEvidence(track_id)
        return self.tracks[track_id]

    def record(
        self,
        track_id: str,
        quality: FaceQualityResult,
        embedding: Optional[List[float]],
        bbox: BoundingBox,
        frame_index: Optional[int] = None,
    ):
        evidence = self.get_or_create(track_id)
        evidence.add_observation(quality=quality, embedding=embedding, bbox=bbox, frame_index=frame_index)

    def get_all_tracks(self) -> List[TrackEvidence]:
        return list(self.tracks.values())

    def clear(self):
        """Disposes all accumulated session data."""
        self.tracks.clear()
