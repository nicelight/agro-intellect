"""SyncStatus enum — MVP has exactly one value: local_only.

⚠️  Future values must be explicitly approved by PRD/spec before
    adding to this enum. server_verified, upload, cloud, backup,
    and remote sync values are forbidden in MVP.
"""

from __future__ import annotations

from enum import Enum


class SyncStatus(str, Enum):
    LOCAL_ONLY = "local_only"
