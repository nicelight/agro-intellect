from __future__ import annotations

from backend.app.api.csrf import CsrfProtection


class TestCsrfProtection:
    def setup_method(self):
        self.protection = CsrfProtection(token="test-token-12345")

    def test_generate_token_returns_non_empty_string(self):
        protection = CsrfProtection()
        token = protection.generate_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_changes_on_each_call(self):
        protection = CsrfProtection()
        t1 = protection.generate_token()
        t2 = protection.generate_token()
        assert t1 != t2

    def test_validate_token_with_correct_token_returns_true(self):
        assert self.protection.validate_token("test-token-12345", "test-token-12345") is True

    def test_validate_token_with_wrong_token_returns_false(self):
        assert self.protection.validate_token("wrong-token", "test-token-12345") is False

    def test_validate_token_with_none_returns_false(self):
        assert self.protection.validate_token(None, "test-token-12345") is False

    def test_validate_token_with_empty_string_returns_false(self):
        assert self.protection.validate_token("", "test-token-12345") is False

    def test_validate_token_with_none_expected_returns_false(self):
        assert self.protection.validate_token("test-token-12345", "") is False

    def test_get_csrf_header_returns_expected(self):
        assert CsrfProtection.get_csrf_header() == "X-CSRF-Token"

    def test_default_constructor_generates_token(self):
        protection = CsrfProtection()
        assert protection._token is not None
        assert len(protection._token) > 0
