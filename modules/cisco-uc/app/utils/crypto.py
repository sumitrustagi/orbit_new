"""Encryption helpers for AppConfig sensitive values."""
import base64
import os

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    from flask import current_app
    key = current_app.config.get("SECRET_KEY", "change-me-to-a-long-random-string")
    padded = key.ljust(32)[:32].encode()
    b64key = base64.urlsafe_b64encode(padded)
    return Fernet(b64key)


def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
