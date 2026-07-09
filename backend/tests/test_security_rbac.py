"""
tests/test_security_rbac.py

Unit tests for the require_role() RBAC dependency factory in core/security.py.
Tests the inner `_check_role` coroutine directly with a fake User-like object,
so no JWT verification, JWKS fetch, or DB connection is needed.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from core.security import require_role  # noqa: E402
from models.user import UserRole  # noqa: E402


@dataclass
class FakeUser:
    role: UserRole


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_allows_user_with_matching_role(self):
        check = require_role(UserRole.ADMIN)
        user = FakeUser(role=UserRole.ADMIN)
        result = await check(current_user=user)  # type: ignore[arg-type]
        assert result is user

    @pytest.mark.asyncio
    async def test_allows_user_matching_one_of_multiple_roles(self):
        check = require_role(UserRole.ADMIN, UserRole.MEMBER)
        user = FakeUser(role=UserRole.MEMBER)
        result = await check(current_user=user)  # type: ignore[arg-type]
        assert result is user

    @pytest.mark.asyncio
    async def test_rejects_user_with_non_matching_role(self):
        check = require_role(UserRole.ADMIN)
        user = FakeUser(role=UserRole.VIEWER)
        with pytest.raises(HTTPException) as exc_info:
            await check(current_user=user)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_error_message_lists_allowed_roles(self):
        check = require_role(UserRole.ADMIN)
        user = FakeUser(role=UserRole.MEMBER)
        with pytest.raises(HTTPException) as exc_info:
            await check(current_user=user)  # type: ignore[arg-type]
        assert "admin" in exc_info.value.detail
