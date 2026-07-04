"""
core/crypto.py

Symmetric encryption for secrets-at-rest (per-user API keys stored in
user_settings.*_key_encrypted columns).

Uses Fernet (AES-128-CBC + HMAC, from the `cryptography` package) with a key
derived from SECRET_KEY via PBKDF2, so we don't need a separate KMS for a
self-hosted deployment. For multi-region/enterprise deployments, swap
`get_fernet()` to pull the key from a real secrets manager (AWS KMS, GCP
Secret Manager, HashiCorp Vault) instead of deriving it from an env var.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from core.config import settings

# Fixed, non-secret salt — the security here comes entirely from SECRET_KEY
# being kept private, not from the salt. A per-deployment salt would require
# also storing/rotating it, which adds operational risk without meaningfully
# increasing security for this threat model (protecting against DB dumps,
# not against an attacker who also has SECRET_KEY).
_KDF_SALT = b"research-platform-static-salt-v1"


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    derived = hashlib.pbkdf2_hmac("sha256", settings.SECRET_KEY.encode("utf-8"), _KDF_SALT, 390_000)
    key = base64.urlsafe_b64encode(derived)
    return Fernet(key)


def encrypt_secret(plaintext: str | None) -> str | None:
    """Encrypts a secret for storage. Returns None unchanged (no key set)."""
    if not plaintext:
        return None
    return get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str | None) -> str | None:
    """
    Decrypts a stored secret. Returns None if there's nothing stored, and
    also returns None (rather than raising) on a corrupted/foreign token —
    callers should treat that as "no usable key" and fall back to shared
    platform defaults instead of crashing the request.
    """
    if not ciphertext:
        return None
    try:
        return get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None
