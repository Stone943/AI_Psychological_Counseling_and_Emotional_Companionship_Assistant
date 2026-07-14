"""AES-256-GCM envelope encryption with random nonce and AAD binding.

Every encrypted value uses a fresh random 12-byte nonce.
AAD binds ciphertext to (object_type, object_id, field_name, key_version).
"""

from __future__ import annotations

import os
from base64 import urlsafe_b64decode, urlsafe_b64encode


class AeadCipher:
    """AES-256-GCM authenticated encryption envelope."""

    NONCE_LENGTH = 12  # 96 bits
    KEY_LENGTH = 32  # 256 bits
    TAG_LENGTH = 16  # GCM auth tag

    def __init__(self, key: bytes) -> None:
        if len(key) != self.KEY_LENGTH:
            raise ValueError(f"AES-256-GCM requires a 32-byte key, got {len(key)}")
        self._key = key

    def encrypt(self, plaintext: str, aad: str = "") -> str:
        """Encrypt plaintext with AAD binding. Returns base64url-encoded envelope."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(self.NONCE_LENGTH)
        aesgcm = AESGCM(self._key)
        aad_bytes = aad.encode("utf-8")
        plaintext_bytes = plaintext.encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, aad_bytes)
        # Envelope: nonce || ciphertext (ciphertext includes GCM tag)
        envelope = nonce + ciphertext
        return urlsafe_b64encode(envelope).decode("ascii")

    def decrypt(self, envelope: str, aad: str = "") -> str | None:
        """Decrypt envelope. Returns None on any failure (wrong key, tampering, etc.)."""
        from cryptography.exceptions import InvalidTag

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            raw = urlsafe_b64decode(envelope.encode("ascii"))
            nonce = raw[: self.NONCE_LENGTH]
            ciphertext = raw[self.NONCE_LENGTH :]
            aesgcm = AESGCM(self._key)
            aad_bytes = aad.encode("utf-8")
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
            return plaintext_bytes.decode("utf-8")
        except (InvalidTag, ValueError, UnicodeDecodeError):
            return None


class EncryptionService:
    """Per-field encryption with key versioning and AAD binding."""

    def __init__(self, key: bytes, key_version: str = "v1") -> None:
        self._cipher = AeadCipher(key)
        self.key_version = key_version

    def encrypt_field(self, plaintext: str, object_type: str, object_id: str, field_name: str) -> str:
        aad = f"{object_type}|{object_id}|{field_name}|{self.key_version}"
        return self._cipher.encrypt(plaintext, aad)

    def decrypt_field(self, envelope: str, object_type: str, object_id: str, field_name: str) -> str | None:
        aad = f"{object_type}|{object_id}|{field_name}|{self.key_version}"
        return self._cipher.decrypt(envelope, aad)
