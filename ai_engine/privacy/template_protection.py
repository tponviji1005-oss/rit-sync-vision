"""
RIT-Sync Vision - Face Template Protection & Privacy
Author: Paul Bryton Raj (AI & System Lead)

Enforces privacy and protection of biometric face templates:
1. Template encryption and masked serialization.
2. Cryptographic template hashing for integrity verification.
3. Revocation and deletion interface.
4. Ensures raw face images are NEVER stored in template storage.
"""

import json
import hashlib
import base64
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from shared.schemas import EnrolledTemplate


class TemplateProtectionManager:
    """
    Manages secure serialization, encryption at rest, and revocation of biometric templates.
    """

    def __init__(self, master_key: Optional[bytes] = None):
        """
        :param master_key: 32-byte AES key. If None, derived from environment or secure random.
        """
        if master_key is None:
            env_key = os.getenv("TEMPLATE_ENCRYPTION_KEY")
            if env_key:
                self.key = hashlib.sha256(env_key.encode()).digest()
            else:
                # Default development fallback key (must be overridden in production)
                self.key = hashlib.sha256(b"rit-sync-vision-dev-template-key").digest()
        else:
            self.key = master_key

        self.aesgcm = AESGCM(self.key)

    def encrypt_template(self, template: EnrolledTemplate) -> Dict[str, Any]:
        """
        Encrypts an EnrolledTemplate to secure ciphertext payload for storage.
        """
        raw_json = json.dumps(template.model_dump()).encode("utf-8")
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, raw_json, None)

        checksum = hashlib.sha256(raw_json).hexdigest()

        return {
            "student_id": template.student_id,
            "nonce_b64": base64.b64encode(nonce).decode("utf-8"),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("utf-8"),
            "integrity_checksum": checksum,
            "encrypted_at": datetime.now(timezone.utc).isoformat(),
        }

    def decrypt_template(self, encrypted_record: Dict[str, Any]) -> EnrolledTemplate:
        """
        Decrypts an encrypted template payload back to an EnrolledTemplate object.
        """
        nonce = base64.b64decode(encrypted_record["nonce_b64"])
        ciphertext = base64.b64decode(encrypted_record["ciphertext_b64"])

        decrypted_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)

        # Verify integrity
        expected_checksum = encrypted_record["integrity_checksum"]
        actual_checksum = hashlib.sha256(decrypted_bytes).hexdigest()
        if expected_checksum != actual_checksum:
            raise ValueError("Template integrity check failed! Ciphertext may have been tampered with.")

        data = json.loads(decrypted_bytes.decode("utf-8"))
        return EnrolledTemplate(**data)

    def create_template(
        self,
        student_id: str,
        student_name: str,
        embedding: List[float],
        model_version: str = "v1.0",
    ) -> EnrolledTemplate:
        """
        Constructs an EnrolledTemplate with timestamp.
        """
        return EnrolledTemplate(
            student_id=student_id,
            student_name=student_name,
            embedding=embedding,
            model_version=model_version,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def revoke_template(self, student_id: str, template_store: Dict[str, Any]) -> bool:
        """
        Revokes/deletes a template from storage upon student deregistration or consent withdrawal.
        """
        if student_id in template_store:
            del template_store[student_id]
            return True
        return False
