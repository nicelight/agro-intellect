"""Pydantic schemas for Farm API endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class FarmResponse(BaseModel):
    farm_id: str
    display_name: str
    status: str
    sync_status: str
    created_at: str | None = None
    updated_at: str | None = None
