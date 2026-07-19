from __future__ import annotations

import pytest

from backend.app import AppSettings
from backend.app.photo_intake import PhotoArtifactStore
from tests.backend.photo_intake.conftest import event_ref_factory, ft005_database


@pytest.fixture
def vision_settings(tmp_path):
    return AppSettings(local_artifact_root=tmp_path / "artifacts")


@pytest.fixture
def vision_artifact_store(vision_settings):
    return PhotoArtifactStore(vision_settings)


__all__ = [
    "event_ref_factory",
    "ft005_database",
    "vision_artifact_store",
    "vision_settings",
]

