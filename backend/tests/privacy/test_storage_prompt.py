from __future__ import annotations

import pytest

from backend.app.privacy.storage_prompt import (
    _UPLOAD_IMPLICATION_PATTERNS,
    StoragePromptValidation,
    validate_storage_prompt,
)
from backend.app.storage.prompt_guard import (
    LOCAL_STORAGE_LIMIT_BYTES,
    LOCAL_STORAGE_LIMIT_MB,
    StorageLimitCheck,
    check_storage_limit,
)


class TestValidateStoragePrompt:
    def test_safe_text_passes(self):
        result = validate_storage_prompt("Store data locally on this device.")
        assert result.verdict == "pass"
        assert result.reason is None
        assert result.matched_patterns == ()

    def test_upload_implies_fail(self):
        result = validate_storage_prompt("upload your photos")
        assert result.verdict == "fail"
        assert any("upload" in p for p in result.matched_patterns)

    def test_backup_to_cloud_fails(self):
        result = validate_storage_prompt("backup to cloud")
        assert result.verdict == "fail"
        assert any("backup" in p for p in result.matched_patterns)
        assert any("cloud" in p for p in result.matched_patterns)

    def test_server_synchronization_fails(self):
        result = validate_storage_prompt("server synchronization is enabled")
        assert result.verdict == "fail"
        assert any("server" in p for p in result.matched_patterns)

    def test_remote_storage_fails(self):
        result = validate_storage_prompt("remote storage option")
        assert result.verdict == "fail"
        assert any("remote" in p for p in result.matched_patterns)

    def test_hosted_service_fails(self):
        result = validate_storage_prompt("hosted service")
        assert result.verdict == "fail"
        assert any("hosted" in p for p in result.matched_patterns)

    def test_online_access_fails(self):
        result = validate_storage_prompt("online access required")
        assert result.verdict == "fail"
        assert any("online" in p for p in result.matched_patterns)

    def test_synchronizing_fails(self):
        result = validate_storage_prompt("synchronizing data")
        assert result.verdict == "fail"
        assert any("synchroniz" in p for p in result.matched_patterns)

    def test_synchronize_fails(self):
        result = validate_storage_prompt("synchronize now")
        assert result.verdict == "fail"
        assert any("synchroniz" in p for p in result.matched_patterns)

    @pytest.mark.parametrize(
        "text",
        [
            "local storage",
            "save on device",
            "store offline",
            "local disk",
            "device memory",
        ],
    )
    def test_various_safe_texts_pass(self, text: str):
        result = validate_storage_prompt(text)
        assert result.verdict == "pass", f"Expected pass for {text!r}"


class TestCheckStorageLimit:
    def test_under_limit_passes(self):
        result = check_storage_limit(100 * 1024 * 1024)
        assert result.within_limit is True
        assert result.current_bytes == 100 * 1024 * 1024
        assert result.limit_bytes == LOCAL_STORAGE_LIMIT_BYTES

    def test_over_limit_fails(self):
        result = check_storage_limit(300 * 1024 * 1024)
        assert result.within_limit is False
        assert result.current_bytes == 300 * 1024 * 1024
        assert result.limit_bytes == LOCAL_STORAGE_LIMIT_BYTES

    def test_exactly_at_limit_passes(self):
        result = check_storage_limit(LOCAL_STORAGE_LIMIT_BYTES)
        assert result.within_limit is True

    def test_messages_are_safe_no_forbidden_patterns(self):
        over = check_storage_limit(300 * 1024 * 1024)
        under = check_storage_limit(100 * 1024 * 1024)
        for msg in (under.message, over.message):
            assert msg is not None
            result = validate_storage_prompt(msg)
            assert result.verdict == "pass", f"Message {msg!r} triggered patterns: {result.matched_patterns}"

    def test_limit_constant_is_correct(self):
        assert LOCAL_STORAGE_LIMIT_MB == 200
        assert LOCAL_STORAGE_LIMIT_BYTES == 200 * 1024 * 1024

    def test_no_server_upload_cloud_in_limit_message(self):
        over = check_storage_limit(300 * 1024 * 1024)
        assert over.message is not None
        msg_lower = over.message.lower()
        for word in ("upload", "backup", "cloud", "server", "sync", "remote", "hosted", "online"):
            assert word not in msg_lower, f"Message contains forbidden word: {word}"
        under = check_storage_limit(100 * 1024 * 1024)
        assert under.message is not None
        msg_lower = under.message.lower()
        for word in ("upload", "backup", "cloud", "server", "sync", "remote", "hosted", "online"):
            assert word not in msg_lower, f"Message contains forbidden word: {word}"


class TestStoragePromptDoesNotMutateSyncStatus:
    """Verify that storage prompt functions never reference or mutate SyncStatus."""

    def test_validate_storage_prompt_returns_pure_validation(self):
        result = validate_storage_prompt("some safe text")
        assert isinstance(result, StoragePromptValidation)
        assert result.verdict == "pass"
        assert not hasattr(result, "sync_status")
        assert not hasattr(result, "status")

    def test_check_storage_limit_does_not_touch_sync(self):
        result = check_storage_limit(50 * 1024 * 1024)
        assert isinstance(result, StorageLimitCheck)
        assert not hasattr(result, "sync_status")
        assert not hasattr(result, "status")
