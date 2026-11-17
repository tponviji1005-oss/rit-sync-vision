"""
RIT-Sync Vision - Camera Input Adapter
Author: Paul Bryton Raj (AI & System Lead)

Provides abstracted camera capture supporting:
1. Physical Webcam (OpenCV device index)                -> bounded by wall-clock time
2. Recorded Video File (for reproducible offline testing) -> bounded by media time
3. Synthetic / Simulated Stream (for automated testing)  -> bounded by media time

Recorded and synthetic sources are processed as fast as possible: the capture window is
measured in media time (frame_index / fps), so a 30 s clip covers 30 s of footage.

Faults are reported through `fault` (a ReasonCode) instead of being silently treated as
the normal end of a session. A teacher stop is requested with `request_stop()`.

Privacy rule: Raw frames are held in memory only during processing and discarded immediately.
"""

import os
import time
import logging
import threading
from typing import Optional, Generator, Tuple, Union
import numpy as np
import cv2

from shared.constants import ReasonCode

logger = logging.getLogger("rit_sync_vision.camera_input")


class CameraInputAdapter:
    """
    Abstracted video input provider for classroom capture.
    Handles startup, bounded time windows, disconnection faults, teacher stop and frame yielding.

    Phase 2 note: a dedicated classroom camera can replace this class by subclassing it and
    overriding `start_capture`, `_read_frame` and `stop_capture`.
    """

    SOURCE_SYNTHETIC = "synthetic"
    SOURCE_FILE = "file"
    SOURCE_LIVE = "live"

    def __init__(
        self,
        source: Union[int, str] = 0,
        fps_target: int = 15,
        capture_width: int = 640,
        capture_height: int = 480,
    ):
        """
        :param source: Device index (e.g. 0 for webcam), video file path, or 'synthetic'
        :param fps_target: Target frames per second to process
        :param capture_width: Requested frame width
        :param capture_height: Requested frame height
        """
        self.source = source
        self.fps_target = fps_target if fps_target > 0 else 15

        if str(source).lower() == "synthetic":
            self.source_kind = self.SOURCE_SYNTHETIC
        elif isinstance(source, int):
            self.source_kind = self.SOURCE_LIVE
        else:
            self.source_kind = self.SOURCE_FILE

        if self.source_kind == self.SOURCE_SYNTHETIC:
            self.capture_width = min(capture_width, 640)
            self.capture_height = min(capture_height, 480)
        else:
            self.capture_width = capture_width
            self.capture_height = capture_height

        self._cap: Optional[cv2.VideoCapture] = None
        self._is_capturing = False
        self._stop_event = threading.Event()

        # Session outcome flags (reset on each start_capture)
        self.fault: Optional[ReasonCode] = None
        self.stopped_by_teacher = False

    # Backwards-compatible alias
    @property
    def _is_synthetic(self) -> bool:
        return self.source_kind == self.SOURCE_SYNTHETIC

    @property
    def is_live(self) -> bool:
        return self.source_kind == self.SOURCE_LIVE

    def check_health(self) -> Tuple[bool, dict]:
        """
        Validates whether the camera source is reachable and capable of providing valid frames.
        :return: (is_healthy, details_dict)
        """
        if self.source_kind == self.SOURCE_SYNTHETIC:
            return True, {
                "source": "synthetic",
                "status": "ready",
                "resolution": f"{self.capture_width}x{self.capture_height}",
            }

        if self.source_kind == self.SOURCE_FILE and not os.path.isfile(str(self.source)):
            return False, {
                "source": "file",
                "status": "cannot_open",
                "error": "Video file not found",
            }

        try:
            temp_cap = cv2.VideoCapture(self.source)
            if not temp_cap.isOpened():
                return False, {
                    "source": self.source_kind,
                    "status": "cannot_open",
                    "error": "Failed to open video capture device/file",
                }
            ret, frame = temp_cap.read()
            temp_cap.release()

            if not ret or frame is None or frame.size == 0:
                return False, {
                    "source": self.source_kind,
                    "status": "unreadable_frame",
                    "error": "Device opened but failed to read initial frame",
                }

            h, w = frame.shape[:2]
            return True, {
                "source": self.source_kind,
                "status": "ready",
                "resolution": f"{w}x{h}",
            }
        except Exception as e:
            logger.error("Camera health check failed: %s", type(e).__name__)
            return False, {"source": self.source_kind, "status": "error", "error": type(e).__name__}

    def start_capture(self) -> bool:
        """Initializes and opens the capture device."""
        self.fault = None
        self.stopped_by_teacher = False
        self._stop_event.clear()

        if self.source_kind == self.SOURCE_SYNTHETIC:
            self._is_capturing = True
            logger.info("Started synthetic capture stream.")
            return True

        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            logger.error("Could not open video source (%s).", self.source_kind)
            self._cap = None
            self._is_capturing = False
            self.fault = ReasonCode.CAMERA_DISCONNECTED
            return False

        if self.is_live:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.capture_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.capture_height)
        self._is_capturing = True
        logger.info("Video capture started on %s source.", self.source_kind)
        return True

    def request_stop(self):
        """Teacher-initiated stop. Safe to call from another thread."""
        self._stop_event.set()

    def stop_capture(self):
        """Releases the camera device and cleans up resources."""
        self._is_capturing = False
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as e:
                logger.warning("Error releasing camera: %s", type(e).__name__)
            finally:
                self._cap = None
        logger.info("Video capture stopped and resources released.")

    def _synthetic_frame(self, frame_idx: int) -> np.ndarray:
        frame = np.zeros((self.capture_height, self.capture_width, 3), dtype=np.uint8)
        cx = int((frame_idx * 15) % self.capture_width)
        cy = self.capture_height // 2
        cv2.circle(frame, (cx, cy), 30, (200, 200, 200), -1)
        return frame

    def _read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self._cap is None or not self._cap.isOpened():
            return False, None
        return self._cap.read()

    def stream_frames(
        self, duration_seconds: float = 30
    ) -> Generator[Tuple[int, float, np.ndarray], None, None]:
        """
        Yields (frame_index, timestamp, frame_bgr) within a bounded duration window.
        Stops when the window ends, the teacher requests a stop, the source ends, or a fault occurs.
        After the generator finishes, inspect `fault` and `stopped_by_teacher`.
        """
        if not self._is_capturing:
            if not self.start_capture():
                return

        frame_interval = 1.0 / self.fps_target
        start_time = time.time()
        frame_idx = 0

        # For recorded video, sample frames to approximate fps_target in media time.
        file_stride = 1
        file_fps = self.fps_target
        if self.source_kind == self.SOURCE_FILE and self._cap is not None:
            native_fps = self._cap.get(cv2.CAP_PROP_FPS) or 0.0
            if native_fps > 0:
                file_fps = native_fps
                file_stride = max(1, int(round(native_fps / self.fps_target)))
        raw_idx = 0

        try:
            while self._is_capturing:
                if self._stop_event.is_set():
                    self.stopped_by_teacher = True
                    logger.info("Capture stopped by teacher request.")
                    break

                # Elapsed time: wall clock for live cameras, media time otherwise
                if self.is_live:
                    elapsed = time.time() - start_time
                elif self.source_kind == self.SOURCE_FILE:
                    elapsed = raw_idx / file_fps
                else:
                    elapsed = frame_idx * frame_interval
                if elapsed >= duration_seconds:
                    logger.info("Bounded capture window of %ss reached.", duration_seconds)
                    break

                loop_start = time.time()

                if self.source_kind == self.SOURCE_SYNTHETIC:
                    ret, frame = True, self._synthetic_frame(frame_idx)
                else:
                    if self._cap is None or not self._cap.isOpened():
                        logger.error("Camera disconnected during capture session.")
                        self.fault = ReasonCode.CAMERA_DISCONNECTED
                        break
                    ret, frame = self._read_frame()
                    raw_idx += 1
                    # Skip frames for recorded video to honour fps_target
                    while ret and self.source_kind == self.SOURCE_FILE and (raw_idx - 1) % file_stride != 0:
                        ret, frame = self._read_frame()
                        raw_idx += 1

                if not ret or frame is None or frame.size == 0:
                    if self.source_kind == self.SOURCE_FILE and frame_idx > 0:
                        logger.info("End of recorded video reached.")
                    else:
                        logger.error("Unreadable frame from camera; treating as disconnection.")
                        self.fault = ReasonCode.CAMERA_DISCONNECTED
                    break

                yield frame_idx, time.time(), frame
                frame_idx += 1

                if self.is_live:
                    sleep_time = frame_interval - (time.time() - loop_start)
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        finally:
            self.stop_capture()
