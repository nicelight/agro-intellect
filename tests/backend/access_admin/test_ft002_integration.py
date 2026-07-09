from __future__ import annotations

from pathlib import Path


TRACEABILITY = {
    "FT-002-BHV-001": {
        ".memory-bank/behavior-specs/FT-002-BHV-001-idempotent-canonical-bootstrap.behavior.json": [
            (
                "tests/backend/access_admin/test_ft002_farm_bootstrap.py",
                "test_canonical_bootstrap_is_idempotent_and_preserves_archived_state",
            ),
            (
                "tests/backend/access_admin/test_ft002_farm_bootstrap.py",
                "test_ft002_postgresql_bootstrap_first_partial_repeat_and_rollback",
            ),
        ],
    },
    "FT-002-BHV-002": {
        ".memory-bank/behavior-specs/FT-002-BHV-002-engineer-create-immediate-access.behavior.json": [
            (
                "tests/backend/access_admin/test_ft002_farm_plant_services.py",
                "test_engineer_create_commits_creator_grant_and_two_audits_atomically",
            ),
            (
                "tests/backend/api/test_ft002_integration_flow.py",
                "test_engineer_integrated_create_select_rename_and_management_denial",
            ),
        ],
    },
    "FT-002-BHV-003": {
        ".memory-bank/behavior-specs/FT-002-BHV-003-archive-grant-restore.behavior.json": [
            (
                "tests/backend/access_admin/test_ft002_grant_lifecycle.py",
                "test_archived_grant_administration_persists_without_mutating_plant_or_identity",
            ),
            (
                "tests/backend/api/test_ft002_integration_flow.py",
                "test_boss_integrated_archive_grant_restore_preserves_current_permissions",
            ),
        ],
    },
    "FT-002-BHV-004": {
        ".memory-bank/behavior-specs/FT-002-BHV-004-truthful-create-persistence-errors.behavior.json": [
            (
                "tests/backend/access_admin/test_ft002_farm_plant_services.py",
                "test_named_plant_key_unique_race_is_the_only_integrity_conflict",
            ),
            (
                "tests/backend/api/test_ft002_plant_routes.py",
                "test_generic_create_persistence_failure_is_not_key_conflict",
            ),
            (
                "tests/backend/api/test_ft002_plant_routes.py",
                "test_farm_persistence_failure_uses_farm_specific_error",
            ),
        ],
    },
}


def test_ft002_behavior_specs_have_direct_executable_traceability():
    """Keep the W4 integration gate tied to concrete tests, not prose only."""

    for behavior_id, spec_map in TRACEABILITY.items():
        assert behavior_id.startswith("FT-002-BHV-")
        for behavior_path, test_refs in spec_map.items():
            spec = Path(behavior_path)
            assert spec.exists(), behavior_path
            assert behavior_id in spec.read_text(encoding="utf-8")
            for test_file, test_name in test_refs:
                source_path = Path(test_file)
                assert source_path.exists(), test_file
                source = source_path.read_text(encoding="utf-8")
                assert f"def {test_name}" in source, f"{behavior_id}: {test_name}"
