"""Pydantic schemas for auth endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    login_identifier: str


class LoginResponse(BaseModel):
    session_token: str
    session_ref: str
    expires_at: str


class LogoutResponse(BaseModel):
    status: str


class MeResponse(BaseModel):
    state: str
    account_id: str | None = None
    farm_id: str | None = None
    membership_id: str | None = None
    role: str | None = None
    membership_status: str | None = None
    resolved_at: str | None = None
