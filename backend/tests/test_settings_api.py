"""
tests/test_settings_api.py

Unit tests for the settings update semantics in api/settings.py.

`apply_settings_update()` is a plain function (no DB session, no FastAPI
dependency injection), so it's tested directly with a lightweight fake
"row" object — no Postgres connection needed to verify the business logic
of "omitted vs empty-string vs real value" key handling.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.settings import _to_read_schema, apply_settings_update  # noqa: E402
from core.crypto import decrypt_secret  # noqa: E402
from schemas.settings import UserSettingsUpdate  # noqa: E402


@dataclass
class FakeSettingsRow:
    """Stand-in for the UserSettings ORM model — same attribute surface, no DB."""
    openrouter_key_encrypted: str | None = None
    groq_key_encrypted: str | None = None
    tavily_key_encrypted: str | None = None
    preferred_model: str | None = None
    default_max_sources: int = 10
    default_citation_style: str = "apa"


class TestApplySettingsUpdate:
    def test_omitted_field_leaves_existing_key_untouched(self):
        row = FakeSettingsRow(openrouter_key_encrypted="existing-ciphertext")
        apply_settings_update(row, UserSettingsUpdate())  # nothing set
        assert row.openrouter_key_encrypted == "existing-ciphertext"

    def test_setting_a_new_key_value_encrypts_and_stores_it(self):
        row = FakeSettingsRow()
        apply_settings_update(row, UserSettingsUpdate(openrouter_api_key="sk-or-v1-newkey"))
        assert row.openrouter_key_encrypted is not None
        assert decrypt_secret(row.openrouter_key_encrypted) == "sk-or-v1-newkey"

    def test_empty_string_explicitly_clears_an_existing_key(self):
        row = FakeSettingsRow(groq_key_encrypted="some-existing-ciphertext")
        apply_settings_update(row, UserSettingsUpdate(groq_api_key=""))
        assert row.groq_key_encrypted is None

    def test_updates_all_three_keys_independently(self):
        row = FakeSettingsRow()
        apply_settings_update(
            row,
            UserSettingsUpdate(
                openrouter_api_key="or-key",
                groq_api_key="groq-key",
                tavily_api_key="tvly-key",
            ),
        )
        assert decrypt_secret(row.openrouter_key_encrypted) == "or-key"
        assert decrypt_secret(row.groq_key_encrypted) == "groq-key"
        assert decrypt_secret(row.tavily_key_encrypted) == "tvly-key"

    def test_updates_preferences_independently_of_keys(self):
        row = FakeSettingsRow()
        apply_settings_update(
            row,
            UserSettingsUpdate(default_max_sources=15, default_citation_style="ieee"),
        )
        assert row.default_max_sources == 15
        assert row.default_citation_style == "ieee"
        assert row.openrouter_key_encrypted is None  # untouched

    def test_preferred_model_updates_independently(self):
        row = FakeSettingsRow(preferred_model="deepseek/deepseek-chat-v3:free")
        apply_settings_update(row, UserSettingsUpdate(preferred_model="qwen/qwen3-8b:free"))
        assert row.preferred_model == "qwen/qwen3-8b:free"


class TestToReadSchema:
    def test_never_exposes_decrypted_or_encrypted_key_values(self):
        row = FakeSettingsRow(openrouter_key_encrypted="some-ciphertext-blob")
        result = _to_read_schema(row)
        result_dict = result.model_dump()
        assert "some-ciphertext-blob" not in str(result_dict)
        assert "openrouter_key_encrypted" not in result_dict

    def test_reports_key_configured_flags_correctly(self):
        row = FakeSettingsRow(openrouter_key_encrypted="x", groq_key_encrypted=None, tavily_key_encrypted="y")
        result = _to_read_schema(row)
        assert result.openrouter_key_configured is True
        assert result.groq_key_configured is False
        assert result.tavily_key_configured is True

    def test_preferences_pass_through_unchanged(self):
        row = FakeSettingsRow(default_max_sources=7, default_citation_style="mla")
        result = _to_read_schema(row)
        assert result.default_max_sources == 7
        assert result.default_citation_style == "mla"
