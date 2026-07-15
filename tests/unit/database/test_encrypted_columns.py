"""Verify AES-256-GCM encryption with AAD binding."""

from __future__ import annotations

import os

import pytest

from mental_health_api.database.encryption import AeadCipher, EncryptionService


class TestAeadCipher:
    def test_roundtrip(self) -> None:
        key = os.urandom(32)
        cipher = AeadCipher(key)
        plaintext = "Hello, sensitive data!"
        envelope = cipher.encrypt(plaintext, aad="test|123|field|v1")
        decrypted = cipher.decrypt(envelope, aad="test|123|field|v1")
        assert decrypted == plaintext

    def test_wrong_aad_fails(self) -> None:
        key = os.urandom(32)
        cipher = AeadCipher(key)
        envelope = cipher.encrypt("secret", aad="obj|1|f|v1")
        result = cipher.decrypt(envelope, aad="obj|2|f|v1")
        assert result is None

    def test_wrong_key_fails(self) -> None:
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        cipher1 = AeadCipher(key1)
        cipher2 = AeadCipher(key2)
        envelope = cipher1.encrypt("secret")
        result = cipher2.decrypt(envelope)
        assert result is None

    def test_tampered_envelope_fails(self) -> None:
        key = os.urandom(32)
        cipher = AeadCipher(key)
        envelope = cipher.encrypt("secret")
        # Tamper with the envelope
        import base64

        raw = base64.urlsafe_b64decode(envelope.encode())
        tampered = bytearray(raw)
        tampered[-1] ^= 0xFF  # flip last byte
        tampered_env = base64.urlsafe_b64encode(bytes(tampered)).decode()
        result = cipher.decrypt(tampered_env)
        assert result is None

    def test_key_length_validation(self) -> None:
        with pytest.raises(ValueError):
            AeadCipher(b"short-key")

    def test_deterministic_nonce(self) -> None:
        """Each encryption uses a unique random nonce."""
        key = os.urandom(32)
        cipher = AeadCipher(key)
        e1 = cipher.encrypt("same-text")
        e2 = cipher.encrypt("same-text")
        assert e1 != e2  # Different nonces produce different ciphertexts


class TestEncryptionService:
    def test_field_encryption(self) -> None:
        key = os.urandom(32)
        svc = EncryptionService(key, key_version="v1")
        ct = svc.encrypt_field("my-secret", "Message", "msg-123", "content")
        pt = svc.decrypt_field(ct, "Message", "msg-123", "content")
        assert pt == "my-secret"

    def test_aad_binding_prevents_cross_field_read(self) -> None:
        key = os.urandom(32)
        svc = EncryptionService(key)
        ct = svc.encrypt_field("top-secret", "Message", "msg-1", "content")
        # Try decrypting as a different field
        result = svc.decrypt_field(ct, "Message", "msg-1", "title")
        assert result is None
