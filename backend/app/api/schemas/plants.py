"""Pydantic schemas for Plant API endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class PlantResponse(BaseModel):
    plant_id: str
    farm_id: str
    canonical_label: str
    display_name: str
    state: str
    created_by_actor_ref: str
    created_at: str | None = None
    archived_at: str | None = None
    archived_by_actor_ref: str | None = None
    archive_reason: str | None = None
    restored_at: str | None = None
    restored_by_actor_ref: str | None = None


class PlantListResponse(BaseModel):
    plants: list[PlantResponse]
    total: int
