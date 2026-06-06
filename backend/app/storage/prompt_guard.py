"""Storage limit guard — warns at 200 MB local storage."""
from __future__ import annotations

from dataclasses import dataclass


LOCAL_STORAGE_LIMIT_MB: int = 200
LOCAL_STORAGE_LIMIT_BYTES: int = 200 * 1024 * 1024


@dataclass(frozen=True)
class StorageLimitCheck:
    within_limit: bool
    current_bytes: int
    limit_bytes: int
    message: str | None = None


def check_storage_limit(current_bytes: int, limit_bytes: int = LOCAL_STORAGE_LIMIT_BYTES) -> StorageLimitCheck:
    if current_bytes <= limit_bytes:
        return StorageLimitCheck(
            within_limit=True,
            current_bytes=current_bytes,
            limit_bytes=limit_bytes,
            message="Local storage is within the 200 MB limit.",
        )
    return StorageLimitCheck(
        within_limit=False,
        current_bytes=current_bytes,
        limit_bytes=limit_bytes,
        message="Local storage has reached 200 MB. Please free up space locally.",
    )
