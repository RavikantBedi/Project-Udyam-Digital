"""Encryption helpers for sensitive values (e.g. LLM API keys)."""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet-compatible key from the app encryption key using SHA-256."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class SecretStore:
    """Encrypt / decrypt sensitive strings using a key derived from
    ``APP_ENCRYPTION_KEY``.

    Never store or return plaintext API keys.  Only ciphertext is persisted.
    """

    def __init__(self, secret: str) -> None:
        self._fernet = Fernet(_derive_key(secret))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    def mask(self, value: str | None) -> str:
        """Return a safe display representation — last 4 chars only."""
        if not value:
            return ""
        return "•" * max(0, len(value) - 4) + value[-4:]
