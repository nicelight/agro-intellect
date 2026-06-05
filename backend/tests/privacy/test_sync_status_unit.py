from __future__ import annotations

import pytest

from backend.app.access.models import Farm, FarmStatus
from backend.app.config import SyncStatus


def test_sync_status_has_exactly_one_value_local_only():
    values = [v.value for v in SyncStatus]
    assert values == ["local_only"]


def test_sync_status_members_are_only_local_only():
    members = list(SyncStatus)
    assert len(members) == 1
    assert members[0] is SyncStatus.LOCAL_ONLY
    assert members[0].value == "local_only"


def test_farm_model_defaults_to_local_only():
    farm = Farm(farm_id="f1", display_name="Test")
    assert farm.sync_status is SyncStatus.LOCAL_ONLY
    assert farm.sync_status.value == "local_only"


def test_farm_local_only_in_safe_dict():
    farm = Farm(farm_id="f1", display_name="Test")
    d = farm.to_safe_dict()
    assert d["sync_status"] == "local_only"


def test_sync_status_cannot_be_set_to_invalid_value():
    with pytest.raises(ValueError):
        SyncStatus("server_verified")

    with pytest.raises(ValueError):
        SyncStatus("upload_status")

    with pytest.raises(ValueError):
        SyncStatus("cloud_availability")

    with pytest.raises(ValueError):
        SyncStatus("remote_backup")
