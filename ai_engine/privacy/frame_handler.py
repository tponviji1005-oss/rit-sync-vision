"""
RIT-Sync Vision - Privacy Frame Handler
Author: Paul Bryton Raj (AI & System Lead)

Enforces privacy-by-default rules:
1. Frame existence in volatile memory only.
2. Immediate memory release upon frame processing.
3. Verification that no raw classroom image or video frames are committed or persisted to disk.
"""

import os
import re
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

    # Media extensions that must never appear in storage or logs (name kept for compatibility)
    ALLOWED_IMAGE_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff",
        ".mp4", ".avi", ".mov", ".mkv", ".npy", ".npz",
    }
    FORBIDDEN_MEDIA_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS

    # Base64 signatures of JPEG / PNG payloads, and 32+ consecutive floats (an embedding dump)
    _BIOMETRIC_PATTERNS = [
        re.compile(r"/9j/[A-Za-z0-9+/]{40}"),
        re.compile(r"iVBORw0KGgo[A-Za-z0-9+/]{40}"),
        re.compile(r"(?:-?\d+\.\d+\s*,\s*){31,}-?\d+\.\d+"),
    ]
    LOG_EXTENSIONS = {".log", ".txt", ".jsonl"}

    @classmethod
    def audit_logs_for_biometrics(cls, root_dir: str) -> Tuple[bool, list]:
        """
        Scans log files under root_dir/logs and root_dir/storage for embedded image data
        or raw embedding vectors.
        :return: (is_clean, violations_list)
        """
        violations = []
        for d in (os.path.join(root_dir, "logs"), os.path.join(root_dir, "storage")):
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if os.path.splitext(f)[1].lower() not in cls.LOG_EXTENSIONS:
                        continue
                    path = os.path.join(root, f)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                            text = fh.read()
                    except OSError:
                        continue
                    if any(p.search(text) for p in cls._BIOMETRIC_PATTERNS):
                        violations.append(path)
        return (len(violations) == 0), violations

    @classmethod
    def audit_storage_cleanliness(cls, root_dir: str) -> Tuple[bool, list]:
        """
        Scans storage/ and logs/ under root_dir to ensure no image or video media files have been saved.
        :return: (is_clean, violations_list)
        """
        violations = []
        target_dirs = [
            os.path.join(root_dir, "storage"),
            os.path.join(root_dir, "logs"),
        ]

        for d in target_dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f == ".gitkeep":
                        continue
                    ext = os.path.splitext(f)[1].lower()
                    if ext in cls.FORBIDDEN_MEDIA_EXTENSIONS:
                        violations.append(os.path.join(root, f))

        return (len(violations) == 0), violations
