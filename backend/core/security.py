"""
core/security.py

Authentication via Clerk (free tier).

Clerk issues short-lived JWTs to the frontend after sign-in. The frontend
sends these as a Bearer token on every API request. We verify the JWT's
signature against Clerk's JWKS endpoint and resolve it to a local `User`
row (synced from Clerk via webhook — see api/auth.py for the webhook
handler that keeps `users` in sync).

This module also exposes `require_role()` for simple role-based access
control (RBAC) on top of the verified user.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from database.connection import get_db
from models.user import User, UserRole

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    """
    Clerk publishes a JWKS (JSON Web Key Set) per-instance at:
      {CLERK_JWT_ISSUER}/.well-known/jwks.json
    PyJWKClient handles fetching + caching the signing keys for us.
    """
    jwks_url = f"{settings.CLERK_JWT_ISSUER.rstrip('/')}/.well-known/jwks.json"
    return PyJWKClient(jwks_url)


def _decode_clerk_token(token: str) -> dict:
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.CLERK_JWT_ISSUER,
            options={"verify_aud": False},  # Clerk doesn't set a fixed `aud` by default
        )
        return payload
    except jwt.PyJWTError as exc:
        logger.warning("Clerk JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: verifies the Clerk JWT and returns the matching
    local `User` row. Raises 401 if the token is missing/invalid, or 404
    if the user hasn't been synced yet (webhook race / first request).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_clerk_token(credentials.credentials)
    clerk_id = payload.get("sub")
    if not clerk_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject claim")

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found — Clerk webhook sync may still be in progress",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")

    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for simple RBAC:

        @router.delete(...)
        async def admin_only(user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    """

    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return _check_role
