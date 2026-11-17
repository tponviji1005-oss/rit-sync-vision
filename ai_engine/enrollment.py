"""
RIT-Sync Vision - Face Enrollment (Template Generation)
Author: Paul Bryton Raj (AI & System Lead)

Turns an authorized enrollment image into an EnrolledTemplate:
    image -> detect exactly one face -> quality gate -> encode -> template

Responsibility split:
- AI engine: produce the template (this module). The source image is never written to disk here.
- Backend: authorization, consent records, encryption at rest (TemplateProtectionManager)
  and storage/revocation of templates.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np

from shared.constants import ReasonCode
from shared.schemas import EnrolledTemplate
from ai_engine.detection.face_detector import FaceDetector
from ai_engine.recognition.face_encoder import FaceEncoder
from ai_engine.privacy.template_protection import TemplateProtectionManager


@dataclass
class EnrollmentResult:
    success: bool
    template: Optional[EnrolledTemplate] = None
    reason_codes: List[ReasonCode] = field(default_factory=list)
    message: str = ""


class FaceEnroller:
    def __init__(
        self,
        detector: Optional[FaceDetector] = None,
        encoder: Optional[FaceEncoder] = None,
        min_face_size: int = 80,
    ):
        """
        :param min_face_size: Enrollment requires larger faces than live capture.
        """
        self.detector = detector or FaceDetector(min_face_size=min_face_size)
        self.encoder = encoder or FaceEncoder(min_face_size=min_face_size)

    def enroll_images(
        self, student_id: str, student_name: str, images_bgr: List[np.ndarray]
    ) -> EnrollmentResult:
        """
        Enrolls a student from one or more images. Embeddings of all accepted images are averaged.
        Every image must contain exactly one usable face, otherwise it is rejected.
        """
        embeddings = []
        reasons: List[ReasonCode] = []

        for img in images_bgr:
            dets = self.detector.detect_faces(img)
            if len(dets) != 1:
                reasons.append(ReasonCode.INSUFFICIENT_QUALITY if not dets else ReasonCode.CONFLICTING_IDENTITY)
                continue
            det = dets[0]
            if not det.quality.is_usable:
                reasons.extend(r for r in det.quality.reason_codes if r not in reasons)
                det.release()
                continue
            emb = self.encoder.encode(
                det.face_crop, enforce_quality=False, source_frame=det.source_frame, face_row=det.face_row
            )
            det.release()
            if emb is not None:
                embeddings.append(np.asarray(emb, dtype=np.float32))

        if not embeddings:
            return EnrollmentResult(
                success=False,
                reason_codes=reasons or [ReasonCode.INSUFFICIENT_QUALITY],
                message="No image contained exactly one usable face.",
            )

        mean = np.mean(embeddings, axis=0)
        mean /= np.linalg.norm(mean) + 1e-12
        template = TemplateProtectionManager.create_template(
            student_id=student_id,
            student_name=student_name,
            embedding=[round(float(v), 6) for v in mean],
            model_version=self.encoder.model_version,
        )
        return EnrollmentResult(
            success=True,
            template=template,
            reason_codes=reasons,
            message=f"Enrolled from {len(embeddings)} of {len(images_bgr)} image(s).",
        )
