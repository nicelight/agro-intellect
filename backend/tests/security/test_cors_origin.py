from __future__ import annotations

import pytest

from backend.app.api.errors import AppError
from backend.app.security.cors_origin import validate_cors_config, validate_cors_origin


class TestValidateCorsOrigin:
    def test_matching_origin_returns_true(self):
        assert validate_cors_origin("http://localhost:5173", ("http://localhost:5173",)) is True

    def test_matching_origin_among_multiple_returns_true(self):
        assert validate_cors_origin(
            "http://192.168.1.100:8080",
            ("http://localhost:5173", "http://192.168.1.100:8080"),
        ) is True

    def test_non_matching_origin_returns_false(self):
        assert validate_cors_origin("http://evil.com", ("http://localhost:5173",)) is False

    def test_empty_allowed_origins_returns_false(self):
        assert validate_cors_origin("http://localhost:5173", ()) is False

    def test_none_origin_returns_false(self):
        assert validate_cors_origin(None, ("http://localhost:5173",)) is False

    def test_empty_string_origin_returns_false(self):
        assert validate_cors_origin("", ("http://localhost:5173",)) is False

    def test_case_sensitive_mismatch_returns_false(self):
        assert validate_cors_origin("HTTP://LOCALHOST:5173", ("http://localhost:5173",)) is False


class TestValidateCorsConfig:
    def test_empty_list_raises_app_error(self):
        with pytest.raises(AppError) as exc:
            validate_cors_config(())
        assert exc.value.code == "invalid_config"

    def test_wildcard_origin_raises_app_error(self):
        with pytest.raises(AppError) as exc:
            validate_cors_config(("*",))
        assert exc.value.code == "invalid_config"

    def test_wildcard_among_valid_origins_raises_app_error(self):
        with pytest.raises(AppError):
            validate_cors_config(("http://localhost:5173", "*"))

    def test_valid_origins_passes(self):
        validate_cors_config(("http://localhost:5173", "http://192.168.1.100:8080"))
