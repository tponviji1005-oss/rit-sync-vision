"""
Unit tests for Face Registration Interface and Template Protection
"""

import unittest
import numpy as np
from ai_engine.recognition.face_encoder import FaceEncoder
from ai_engine.privacy.template_protection import TemplateProtectionManager
from shared.schemas import EnrolledTemplate


class TestRegistrationAndTemplates(unittest.TestCase):
    def setUp(self):
        self.encoder = FaceEncoder()
        self.prot_mgr = TemplateProtectionManager()

    def test_encode_dimensions_and_norm(self):
        # Create a synthetic face-like crop with gradients
        crop = np.zeros((100, 100, 3), dtype=np.uint8)
        crop[:, :50] = 60
        crop[:, 50:] = 180
        # Add pattern for gradients
        crop[30:70, 30:70] = 120

        emb = self.encoder.encode(crop, enforce_quality=False)
        self.assertIsNotNone(emb)
        self.assertEqual(len(emb), 128)

        # Verify L2 norm is approximately 1.0
        norm = np.linalg.norm(np.array(emb))
        self.assertAlmostEqual(norm, 1.0, places=3)

    def test_template_encryption_and_decryption(self):
        sample_emb = [0.1] * 128
        template = self.prot_mgr.create_template(
            student_id="STU001",
            student_name="Aarav Sharma",
            embedding=sample_emb,
        )

        # Encrypt
        encrypted = self.prot_mgr.encrypt_template(template)
        self.assertIn("ciphertext_b64", encrypted)
        self.assertIn("nonce_b64", encrypted)
        self.assertEqual(encrypted["student_id"], "STU001")

        # Decrypt
        decrypted = self.prot_mgr.decrypt_template(encrypted)
        self.assertEqual(decrypted.student_id, "STU001")
        self.assertEqual(decrypted.student_name, "Aarav Sharma")
        self.assertEqual(decrypted.embedding, sample_emb)

    def test_tamper_detection(self):
        sample_emb = [0.1] * 128
        template = self.prot_mgr.create_template(
            student_id="STU002",
            student_name="Bhavya Patel",
            embedding=sample_emb,
        )
        encrypted = self.prot_mgr.encrypt_template(template)

        # Tamper checksum
        encrypted["integrity_checksum"] = "badchecksum00000000000000000000"
        with self.assertRaises(ValueError):
            self.prot_mgr.decrypt_template(encrypted)

    def test_revocation(self):
        store = {"STU001": {"encrypted": "data"}}
        success = self.prot_mgr.revoke_template("STU001", store)
        self.assertTrue(success)
        self.assertNotIn("STU001", store)


if __name__ == "__main__":
    unittest.main()
