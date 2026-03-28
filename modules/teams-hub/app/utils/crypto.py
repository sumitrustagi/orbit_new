"""
Simple symmetric encryption for sensitive AppConfig values.
Uses Fernet (AES-128-CBC with HMAC) from the cryptography library.
"""
import base64
import os

from cryptography.fernet import Fernet


def _get_key() -> bytes:
    """
    Derive a Fernet key from the ENCRYPTION_KEY env var.
    Falls back to SECRET_KEY if ENCRYPTION_KEY is not set.
    """
    raw = os.environ.get("ENCRYPTION_KEY") or os.environ.get("SECRET_KEY", "")
    if not raw:
        raise RuntimeError("No ENCRYPTION_KEY or SECRET_KEY configured.")
    # Fernet requires a 32-byte URL-safe base64 key; derive one deterministically
    key = base64.urlsafe_b64encode(raw.encode().ljust(32, b"\0")[:32])
    return key


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return a base64-encoded ciphertext."""
    f = Fernet(_get_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext back to plaintext."""
    f = Fernet(_get_key())
    return f.decrypt(ciphertext.encode()).decode()
