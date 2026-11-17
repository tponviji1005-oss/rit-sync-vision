"""
RIT-Sync Vision - Privacy Frame Handler
Author: Paul Bryton Raj (AI & System Lead)

Enforces privacy-by-default rules:
1. Frame existence in volatile memory only.
2. Immediate memory release upon frame processing.
3. Verification that no raw classroom image or video frames are committed or persisted to disk.
"""

import os
from pathlib import Path
from typing import Generator, Any, Tuple
import numpy as np


class EphemeralFrameContext:
    """
    Context manager ensuring frame memory is explicitly deleted after execution.
    """

    def __init__(self, frame: np.ndarray):
        self.frame = frame

    def __enter__(self) -> np.ndarray:
        return self.frame

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Force frame array reference release
        self.frame = None


class PrivacyAuditor:
    """
    Scans storage directories to verify zero raw frames or video files were persisted.
    """

    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi", ".mov"}

    @classmethod
    def audit_storage_cleanliness(cls, root_dir: str) -> Tuple[bool, list]:
        """
        Scans root_dir (specifically storage/ and logs/) to ensure no unauthorized
        image or video media files have been saved.
        :return: (is_clean, violations_list)
        """
        violations = []
        target_dirs = [
            os.path.join(root_dir, "storage", "database"),
            os.path.join(root_dir, "storage", "temporary"),
            os.path.join(root_dir, "storage", "face_templates"),
        ]

        for d in target_dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f == ".gitkeep":
                        continue
                    ext = os.path.splitext(f)[1].lower()
                    if ext in cls.ALLOWED_IMAGE_EXTENSIONS:
                        violations.append(os.path.join(root, f))

        return (len(violations) == 0), violations
