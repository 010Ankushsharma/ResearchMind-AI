"""
api/auth.py

Clerk webhook handler.

Clerk (free tier) owns sign-up/sign-in/session management entirely on the
frontend. Whenever a user is created/updated/deleted in Clerk, it POSTs a
signed webhook event here so we can keep our local `users` table in sync
(needed for foreign keys on research_sessions/reports/etc).

Routes:
  POST /api/auth/webhook   - Clerk webhook receiver (user.created/updated/deleted)
  GET  /api/auth/me        - return the currently authenticated user
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from core.config import settings
from core.security import get_current_user
from database.connection import get_db
from models.user import User
from schemas.user import UserRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _verify_clerk_webhook(request: Request) -> dict:
    """Verifies the Svix signature Clerk attaches to every webhook delivery."""
    if not settings.CLERK_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="CLERK_WEBHOOK_SECRET is not configured")

    payload = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }

    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        return wh.verify(payload, headers)
    except WebhookVerificationError as exc:
        logger.warning("Clerk webhook signature verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature") from exc


def _primary_email(clerk_user_data: dict) -> str | None:
    email_addresses = clerk_user_data.get("email_addresses", [])
    primary_id = clerk_user_data.get("primary_email_address_id")
    for entry in email_addresses:
        if entry.get("id") == primary_id:
            return entry.get("email_address")
    return email_addresses[0]["email_address"] if email_addresses else None


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    event = await _verify_clerk_webhook(request)
    event_type = event.get("type")
    data = event.get("data", {})
    clerk_id = data.get("id")

    if not clerk_id:
        raise HTTPException(status_code=400, detail="Missing user id in webhook payload")

    if event_type == "user.created":
        existing = await db.execute(select(User).where(User.clerk_id == clerk_id))
        if existing.scalar_one_or_none():
            logger.info("Clerk user %s already exists locally — skipping create", clerk_id)
            return

        full_name = " ".join(filter(None, [data.get("first_name"), data.get("last_name")])) or None
        db.add(
            User(
                clerk_id=clerk_id,
                email=_primary_email(data) or f"{clerk_id}@unknown.local",
                full_name=full_name,
                avatar_url=data.get("image_url"),
            )
        )
        logger.info("Synced new Clerk user %s", clerk_id)

    elif event_type == "user.updated":
        result = await db.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user:
            full_name = " ".join(filter(None, [data.get("first_name"), data.get("last_name")])) or user.full_name
            user.full_name = full_name
            user.avatar_url = data.get("image_url") or user.avatar_url
            email = _primary_email(data)
            if email:
                user.email = email
            logger.info("Updated Clerk user %s", clerk_id)

    elif event_type == "user.deleted":
        result = await db.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_active = False
            logger.info("Deactivated Clerk user %s (deleted upstream)", clerk_id)

    else:
        logger.debug("Ignoring unhandled Clerk webhook event type: %s", event_type)

    return None


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's profile — used by the frontend on app load."""
    return current_user
