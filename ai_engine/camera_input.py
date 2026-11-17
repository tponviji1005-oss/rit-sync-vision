"""
RIT-Sync Vision - Camera Input Adapter
Author: Paul Bryton Raj (AI & System Lead)

Provides abstracted camera capture supporting:
1. Physical Webcam (OpenCV device index)
2. Recorded Video File (for reproducible offline testing)
3. Synthetic / Simulated Stream (for automated CI/CD and testing)

Privacy rule: Raw frames are held in memory only during processing and discarded immediately.
"""

import time
import logging
from typing import Optional, Generator, Tuple, Union
import numpy as np
import cv2

logger = logging.getLogger("rit_sync_vision.camera_input")


class CameraInputAdapter:
    """
    Abstracted video input provider for classroom capture.
    Handles startup, bounded time windows, reconnection/disconnection, and frame yielding.
    """

    def __init__(
        self,
        source: Union[int, str] = 0,
        fps_target: int = 15,
        capture_width: int = 640,
        capture_height: int = 480,
    ):
        """
        :param source: Device index (e.g. 0 for webcam), file path (string), or 'synthetic'
        :param fps_target: Target frames per second
        :param capture_width: Requested frame width
        :param capture_height: Requested frame height
        """
        self.source = source
        self.fps_target = fps_target
        self._is_synthetic = (str(source).lower() == "synthetic")

        if self._is_synthetic:
            self.capture_width = min(capture_width, 640)
            self.capture_height = min(capture_height, 480)
        else:
            self.capture_width = capture_width
            self.capture_height = capture_height

        self._cap: Optional[cv2.VideoCapture] = None
        self._is_capturing = False

    def check_health(self) -> Tuple[bool, dict]:
        """
        Validates whether the camera source is reachable and capable of providing valid frames.
        :return: (is_healthy, details_dict)
        """
        if self._is_synthetic:
            return True, {
                "source": "synthetic",
                "status": "ready",
                "resolution": f"{self.capture_width}x{self.capture_height}",
            }

        try:
            temp_cap = cv2.VideoCapture(self.source)
            if not temp_cap.isOpened():
                return False, {
                    "source": str(self.source),
                    "status": "cannot_open",
                    "error": "Failed to open video capture device/file",
                }
            ret, frame = temp_cap.read()
            temp_cap.release()

            if not ret or frame is None or frame.size == 0:
                return False, {
                    "source": str(self.source),
                    "status": "unreadable_frame",
                    "error": "Device opened but failed to read initial frame",
                }

            h, w = frame.shape[:2]
            return True, {
                "source": str(self.source),
                "status": "ready",
                "resolution": f"{w}x{h}",
            }
        except Exception as e:
            logger.error(f"Camera health check failed: {e}")
            return False, {"source": str(self.source), "status": "error", "error": str(e)}

    def start_capture(self) -> bool:
        """Initializes and opens the capture device."""
        if self._is_synthetic:
            self._is_capturing = True
            logger.info("Started synthetic capture stream.")
            return True

        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            logger.error(f"Could not open video source: {self.source}")
            self._is_capturing = False
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.capture_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.capture_height)
        self._is_capturing = True
        logger.info(f"Video capture started on source: {self.source}")
        return True

    def stop_capture(self):
        """Releases the camera device and cleans up resources."""
        self._is_capturing = False
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as e:
                logger.warning(f"Error releasing camera: {e}")
            finally:
                self._cap = None
        logger.info("Video capture stopped and resources released.")

    def stream_frames(
        self, duration_seconds: int = 30
    ) -> Generator[Tuple[int, float, np.ndarray], None, None]:
        """
        Yields (frame_index, timestamp, frame_bgr) within a bounded duration window.
        Guarantees capture stops after duration_seconds or when manually stopped.
        """
        if not self._is_capturing:
            if not self.start_capture():
                return

        start_time = time.time()
        frame_interval = 1.0 / self.fps_target if self.fps_target > 0 else 0.05
        frame_idx = 0

        try:
            while self._is_capturing:
                elapsed = time.time() - start_time
                if elapsed >= duration_seconds:
                    logger.info(f"Bounded capture window of {duration_seconds}s reached.")
                    break

                loop_start = time.time()

                if self._is_synthetic:
                    frame = np.zeros((self.capture_height, self.capture_width, 3), dtype=np.uint8)
                    cx = int((frame_idx * 15) % self.capture_width)
                    cy = self.capture_height // 2
                    cv2.circle(frame, (cx, cy), 30, (200, 200, 200), -1)
                    ret = True
                else:
                    if self._cap is None or not self._cap.isOpened():
                        logger.error("Camera disconnected during capture session.")
                        break
                    ret, frame = self._cap.read()

                if not ret or frame is None or frame.size == 0:
                    logger.warning("Empty or unreadable frame received. Ending stream.")
                    break

                yield frame_idx, time.time(), frame
                frame_idx += 1

                elapsed_frame = time.time() - loop_start
                sleep_time = frame_interval - elapsed_frame
                if sleep_time > 0:
                    time.sleep(sleep_time)

        finally:
            self.stop_capture()
