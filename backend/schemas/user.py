"""
schemas/user.py

Pydantic schemas for User-related API requests/responses.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None


class UserCreate(UserBase):
    """Used internally when syncing a new user from a Clerk webhook."""
    clerk_id: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clerk_id: str
    role: UserRole
    is_active: bool
    research_count: int
    created_at: datetime
    updated_at: datetime


class UserPublic(BaseModel):
    """Minimal user info safe to embed in other responses (e.g. report owner)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str | None = None
    avatar_url: str | None = None
