"""Integration tests for SyncStatus contract.

These tests verify that:
- The migration CHECK constraint enforces local_only
- server_verified, upload, cloud, backup fields are absent from touched modules
- Local storage prompts/export flows do not mutate sync status (conceptual mock)
"""

from __future__ import annotations

import pytest

from backend.app.access.models import Farm
from backend.app.config import SyncStatus


# --- Migration CHECK constraint (simulated via model enforcement) ---

def test_migration_check_enforces_local_only():
    """SyncStatus enum itself enforces that only local_only is accepted."""
    assert SyncStatus("local_only") is SyncStatus.LOCAL_ONLY

    invalid = ("server_verified", "upload_status", "cloud_availability",
               "server_copy", "remote_backup", "synced", "pending")
    for val in invalid:
        with pytest.raises(ValueError, match=f"'{val}'"):
            SyncStatus(val)


def test_farm_sync_status_defaults_to_local_only():
    farm = Farm(farm_id="f_integration", display_name="Integration Farm")
    assert farm.sync_status == SyncStatus.LOCAL_ONLY


# --- Negative test: no forbidden fields in touched modules ---

FORBIDDEN_FIELD_SUBSTRINGS = (
    "server_verified",
    "upload_status",
    "cloud_availability",
    "server_copy",
    "remote_backup",
    "upload",
)


def _safe_repr(obj: object) -> str:
    """Return repr without triggering accidental side effects."""
    return repr(obj)


def test_no_server_verified_fields_in_farm_model():
    """Farm must NOT contain server_verified, upload, cloud, or backup fields."""
    farm = Farm(farm_id="f_neg", display_name="Negative")
    r = _safe_repr(farm)
    for forbidden in FORBIDDEN_FIELD_SUBSTRINGS:
        assert forbidden not in r, f"Farm repr contains forbidden field '{forbidden}'"


def test_no_server_verified_fields_in_sync_status_module():
    """SyncStatus module must NOT reference forbidden sync values."""
    for forbidden in FORBIDDEN_FIELD_SUBSTRINGS:
        assert not hasattr(SyncStatus, forbidden.upper()), (
            f"SyncStatus has forbidden member '{forbidden.upper()}'"
        )


def test_farm_to_safe_dict_excludes_forbidden_fields():
    """to_safe_dict must not include server_verified, upload, cloud, or backup keys."""
    farm = Farm(farm_id="f_safe", display_name="Safe")
    d = farm.to_safe_dict()
    for forbidden in FORBIDDEN_FIELD_SUBSTRINGS:
        assert forbidden not in d, (
            f"Farm.to_safe_dict() contains forbidden key '{forbidden}'"
        )


# --- Local storage prompts / export flow cannot mutate sync status ---

def test_local_storage_flow_does_not_mutate_sync_status():
    """Simulate that local prompts/export DON'T change sync_status.

    Because Farm is a frozen dataclass, properties cannot be accidentally
    mutated. If a service tried to assign farm.sync_status = <other>,
    it would raise a FrozenInstanceError.
    """
    farm = Farm(farm_id="f_export", display_name="Export Farm")
    assert farm.sync_status is SyncStatus.LOCAL_ONLY

    # Even trying to assign a non-existent SyncStatus value fails first
    with pytest.raises(ValueError, match="server_verified"):
        SyncStatus("server_verified")  # type: ignore[arg-type]

    # Frozen dataclass rejects any attribute mutation
    with pytest.raises(AttributeError):
        # noinspection PyDataclass
        farm.sync_status = "local_only"  # type: ignore[misc]

    # Verify immutability holds after attempting assignment
    assert farm.sync_status is SyncStatus.LOCAL_ONLY


def test_sync_status_value_is_always_local_only_string():
    """The underlying string value must always be 'local_only'."""
    farm = Farm(farm_id="f_str", display_name="String Test")
    assert str(farm.sync_status.value) == "local_only"
    assert farm.sync_status == SyncStatus.LOCAL_ONLY
    assert SyncStatus.LOCAL_ONLY == "local_only"
