"""
tests/test_crypto.py

Unit tests for core/crypto.py — the Fernet-based encryption used to store
per-user BYO API keys at rest. Fully offline: Fernet key derivation only
needs SECRET_KEY (already defaulted in core/config.py), no DB/network.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.crypto import decrypt_secret, encrypt_secret, get_fernet  # noqa: E402


class TestEncryptDecryptRoundtrip:
    def test_roundtrip_preserves_plaintext(self):
        secret = "sk-or-v1-abc123superrealkey"
        encrypted = encrypt_secret(secret)
        assert encrypted is not None
        assert decrypt_secret(encrypted) == secret

    def test_ciphertext_does_not_contain_plaintext(self):
        secret = "tvly-superrealsecretvalue"
        encrypted = encrypt_secret(secret)
        assert secret not in encrypted

    def test_encrypting_same_value_twice_yields_different_ciphertext(self):
        # Fernet includes a random IV/timestamp, so encrypting the same
        # plaintext twice must NOT produce identical ciphertext — otherwise
        # an attacker could fingerprint which users share the same key.
        secret = "gsk_identical_key_value"
        first = encrypt_secret(secret)
        second = encrypt_secret(secret)
        assert first != second
        assert decrypt_secret(first) == decrypt_secret(second) == secret


class TestEmptyAndNoneHandling:
    def test_encrypting_none_returns_none(self):
        assert encrypt_secret(None) is None

    def test_encrypting_empty_string_returns_none(self):
        # Empty string is the "clear this key" sentinel at the API layer —
        # it should never produce a storable ciphertext.
        assert encrypt_secret("") is None

    def test_decrypting_none_returns_none(self):
        assert decrypt_secret(None) is None

    def test_decrypting_empty_string_returns_none(self):
        assert decrypt_secret("") is None


class TestCorruptedOrForeignTokens:
    def test_decrypting_garbage_returns_none_not_raises(self):
        assert decrypt_secret("not-a-real-fernet-token") is None

    def test_decrypting_truncated_token_returns_none(self):
        secret = "sk-or-v1-validkey"
        encrypted = encrypt_secret(secret)
        truncated = encrypted[:-5]
        assert decrypt_secret(truncated) is None


class TestFernetSingleton:
    def test_get_fernet_returns_same_instance_when_cached(self):
        # lru_cache means repeated calls (within the same process /
        # SECRET_KEY) must return a usable, consistent key — verified
        # indirectly via successful cross-call decryption.
        f1 = get_fernet()
        encrypted = f1.encrypt(b"hello").decode("utf-8")
        f2 = get_fernet()
        assert f2.decrypt(encrypted.encode("utf-8")) == b"hello"
